from flask import Flask, request, jsonify
import asyncio
import threading
from queue import Queue
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl.types import InputPhoneContact, PeerUser
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
import logging
import uuid
from config import api_id, api_hash

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

clients_data = {}

async def send_code_request(client, phone_number, client_id):
    try:
        app.logger.info(f"Client {client_id}: Sending code request to {phone_number}")
        await client.send_code_request(phone_number)
        app.logger.info(f"Client {client_id}: Code request sent successfully")
        return {'isOK': True}
    except Exception as e:
        app.logger.error(f"Client {client_id}: Error sending code request: {e}")
        return {'isOK': False, 'error': str(e)}

async def sign_in(client, phone_number, code, client_id):
    try:
        app.logger.info(f"Client {client_id}: Attempting to sign in with code {code}")
        await client.sign_in(phone_number, code)
        return {'isOK': True}
    except Exception as e:
        app.logger.error(f"Client {client_id}: Error during sign-in: {e}")
        return {'isOK': False, 'error': str(e)}

async def send_message(client, phone_number, message, client_id):
    try:
        user = await client.get_entity(phone_number)
        
        await client.send_message(user, message)
        app.logger.info(f"Client {client_id}: Message sent to contact with phone number {phone_number}.")

        return {'isOK': True} 

    except (errors.rpcerrorlist.PhoneNumberUnoccupiedError, ValueError, TypeError) as e:
        app.logger.info(f"Client {client_id}: User with phone number {phone_number} not found in contacts or not a Telegram user. Adding to contacts.")
        contact = InputPhoneContact(client_id=0, phone=phone_number, first_name='', last_name='')
        result = await client(ImportContactsRequest([contact]))

        if not result.imported:
            app.logger.error(f"Client {client_id}: Failed to add contact with phone number {phone_number}.")
            return {'isOK': False, 'error': 'Contact not imported'}

        try:
            user = await client.get_entity(phone_number)
            await client.send_message(user, message)
            app.logger.info(f"Client {client_id}: Contact with phone number {phone_number} was added and message sent.")
            return {'isOK': True}
        except Exception as e:
            app.logger.error(f"Client {client_id}: Failed to send message after adding contact with phone number {phone_number}. Error: {e}")
            return {'isOK': False, 'error': str(e)}


async def send_message_to_self(client, message, client_id):
    try:
        app.logger.info(f"Client {client_id}: Attempting to send message to self")
        me = await client.get_me()
        await client.send_message(me.id, message)
        app.logger.info(f"Client {client_id}: Message sent successfully to self")
        return {'isOK': True}
    except Exception as e:
        app.logger.error(f"Client {client_id}: Error sending message to self: {e}")
        return {'isOK': False, 'error': str(e)}

async def disconnect(client, client_id):
    try:
        await client.log_out()
        app.logger.info(f"Client {client_id}: Logged out from Telegram")
        return {'isOK': True}
    except Exception as e:
        app.logger.error(f"Client {client_id}: Error logging out: {e}")
        return {'isOK': False, 'error': str(e)}

def telethon_worker(client_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = TelegramClient(StringSession(), api_id, api_hash)
    request_queue = clients_data[client_id]['request_queue']
    is_authenticated = False
    phone_number = clients_data[client_id]['phone_number']

    async def process_requests():
        nonlocal is_authenticated

        try:
            app.logger.info(f"Client {client_id}: Connecting to Telegram...")
            await client.connect()
            app.logger.info(f"Client {client_id}: Connected to Telegram")

            while True:
                request_data = request_queue.get()

                try:
                    if request_data['type'] == 'send_code_request':
                        if not await client.is_user_authorized():
                            request_data['result'] = await send_code_request(client, phone_number, client_id)
                        else:
                            request_data['result'] = {'isOK': True}

                    elif request_data['type'] == 'sign_in':
                        code = request_data['code']
                        result = await sign_in(client, phone_number, code, client_id)
                        if result['isOK']:
                            is_authenticated = True
                        request_data['result'] = result

                    elif request_data['type'] == 'send_message':
                        if not is_authenticated:
                            request_data['result'] = {'isOK': False, 'error': 'Not authenticated'}
                        else:
                            request_data['result'] = await send_message(client, request_data['to_phone'], request_data['text'], client_id)

                    elif request_data['type'] == 'send_message_to_self':
                        if not is_authenticated:
                            request_data['result'] = {'isOK': False, 'error': 'Not authenticated'}
                        else:
                            request_data['result'] = await send_message_to_self(client, request_data['text'], client_id)

                    elif request_data['type'] == 'disconnect':
                        request_data['result'] = await disconnect(client, client_id)
                        break

                    else:
                        request_data['result'] = {'isOK': False, 'error': 'Invalid request type'}

                except Exception as e:
                    app.logger.error(f"Client {client_id}: Unexpected error: {e}")
                    request_data['result'] = {'isOK': False, 'error': str(e)}
                finally:
                    request_queue.task_done()

        finally:
            app.logger.info(f"Client {client_id}: Disconnecting from Telegram...")
            await client.disconnect()
            app.logger.info(f"Client {client_id}: Disconnected from Telegram")

    try:
        loop.run_until_complete(process_requests())
    finally:
        loop.close()
        del clients_data[client_id]

# Flask routes

@app.route('/auth_by_phone', methods=['POST'])
def auth_by_phone():
    phone_number = request.json.get('phone')
    if not phone_number:
        return jsonify(isOK=False, error="Phone number is required")

    client_id = str(uuid.uuid4())

    if client_id not in clients_data:
        clients_data[client_id] = {
            'request_queue': Queue(),
            'phone_number': phone_number
        }
        threading.Thread(target=telethon_worker, args=(client_id,), daemon=True).start()

    request_data = {'type': 'send_code_request', 'result': None}
    clients_data[client_id]['request_queue'].put(request_data)
    clients_data[client_id]['request_queue'].join()

    if request_data['result']['isOK']:
        return jsonify(isOK=True, client_id=client_id)
    else:
        del clients_data[client_id]
        return jsonify(isOK=False, error=request_data['result']['error'])

@app.route('/auth_by_code', methods=['POST'])
def auth_by_code_handler():
    client_id = request.json.get('client_id')
    code = request.json.get('code')
    if not client_id or not code:
        return jsonify(isOK=False, error="Client ID and code are required")

    if client_id not in clients_data:
        return jsonify(isOK=False, error="Client not registered (send code request first)")

    request_data = {'type': 'sign_in', 'code': code, 'result': None}
    clients_data[client_id]['request_queue'].put(request_data)
    clients_data[client_id]['request_queue'].join()
    return jsonify(request_data['result'])

@app.route('/send_message', methods=['POST'])
def send_message_handler():
    client_id = request.json.get('client_id')
    to_phone = request.json.get('to_phone')
    text = request.json.get('text')
    if not client_id or not to_phone or not text:
        return jsonify(isOK=False, error="Client ID, recipient phone number, and text are required")

    if client_id not in clients_data:
        return jsonify(isOK=False, error="Client not registered (send code request first)")

    request_data = {'type': 'send_message', 'to_phone': to_phone, 'text': text, 'result': None}
    clients_data[client_id]['request_queue'].put(request_data)
    clients_data[client_id]['request_queue'].join()
    return jsonify(request_data['result'])

@app.route('/send_message_to_self', methods=['POST'])
def send_message_to_self_handler():
    client_id = request.json.get('client_id')
    text = request.json.get('text')
    if not client_id or not text:
        return jsonify(isOK=False, error="Client ID and text are required")

    if client_id not in clients_data:
        return jsonify(isOK=False, error="Client not registered (send code request first)")

    request_data = {'type': 'send_message_to_self', 'text': text, 'result': None}
    clients_data[client_id]['request_queue'].put(request_data)
    clients_data[client_id]['request_queue'].join()
    return jsonify(request_data['result'])

@app.route('/get_clients', methods=['GET'])
def get_clients():
    clients_info = [{'client_id': client_id, 'phone_number': clients_data[client_id]['phone_number']}
                    for client_id in clients_data]
    return jsonify(clients=clients_info)

@app.route('/disconnect', methods=['POST'])
def disconnect_handler():
    client_id = request.json.get('client_id')
    if not client_id:
        return jsonify(isOK=False, error="Client ID is required")

    if client_id not in clients_data:
        return jsonify(isOK=False, error="Client not found")

    request_data = {'type': 'disconnect', 'result': None}
    clients_data[client_id]['request_queue'].put(request_data)
    clients_data[client_id]['request_queue'].join()
    return jsonify(request_data['result'])

@app.route('/ping', methods=['GET'])
def ping_handler():
        return jsonify(isOK=True, message="pong")

if __name__ == '__main__':
    app.run(debug=True)
