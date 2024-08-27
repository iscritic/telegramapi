# Telegram API - Flask Server

This project provides an HTTP server built using Flask that integrates with the Telegram API through the Telethon library. The application allows for authentication via phone number, sending messages to yourself or others, and managing Telegram sessions programmatically.

## Features

- **Authentication by Phone Number**: Initiates the authentication process by sending a code to the provided phone number.
- **Authentication by Code**: Completes the authentication process by verifying the code received on the phone.
- **Send Message**: Sends a message to a specified phone number.
- **Send Message to Self**: Sends a message to yourself on Telegram.
- **Disconnect**: Logs out and disconnects the Telegram client.
- **Get Clients**: Retrieves a list of active clients and their associated phone numbers.
- **Ping**: Simple endpoint to verify the server is running.

## Getting Started

### Prerequisites

- Python 3.7+
- Telegram API credentials (`api_id`, `api_hash`)
- Flask
- Telethon

### Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/iscritic/telegramapi.git
    cd telegramapi
    ```

2. Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```

3. Configure your Telegram API credentials by creating a `config.py` file:

    ```python
    # config.py
    api_id = 'YOUR_API_ID'
    api_hash = 'YOUR_API_HASH'
    ```

4. Run the Flask application:

    ```bash
    python app.py
    ```

### Usage

#### Authentication by Phone

Endpoint: `/auth_by_phone`

- **Method**: `POST`
- **Request Body**:

    ```json
    {
        "phone": "PHONE_NUMBER"
    }
    ```

- **Response**:

    ```json
    {
        "isOK": true,
        "client_id": "UNIQUE_CLIENT_ID"
    }
    ```

#### Authentication by Code

Endpoint: `/auth_by_code`

- **Method**: `POST`
- **Request Body**:

    ```json
    {
        "client_id": "UNIQUE_CLIENT_ID",
        "code": "RECEIVED_CODE"
    }
    ```

- **Response**:

    ```json
    {
        "isOK": true
    }
    ```

#### Send Message

Endpoint: `/send_message`

- **Method**: `POST`
- **Request Body**:

    ```json
    {
        "client_id": "UNIQUE_CLIENT_ID",
        "to_phone": "RECIPIENT_PHONE_NUMBER",
        "text": "YOUR_MESSAGE"
    }
    ```

- **Response**:

    ```json
    {
        "isOK": true
    }
    ```

#### Send Message to Self

Endpoint: `/send_message_to_self`

- **Method**: `POST`
- **Request Body**:

    ```json
    {
        "client_id": "UNIQUE_CLIENT_ID",
        "text": "YOUR_MESSAGE"
    }
    ```

- **Response**:

    ```json
    {
        "isOK": true
    }
    ```

#### Get Clients

Endpoint: `/get_clients`

- **Method**: `GET`
- **Response**:

    ```json
    {
        "clients": [
            {
                "client_id": "UNIQUE_CLIENT_ID",
                "phone_number": "PHONE_NUMBER"
            }
        ]
    }
    ```

#### Disconnect

Endpoint: `/disconnect`

- **Method**: `POST`
- **Request Body**:

    ```json
    {
        "client_id": "UNIQUE_CLIENT_ID"
    }
    ```

- **Response**:

    ```json
    {
        "isOK": true
    }
    ```

#### Ping

Endpoint: `/ping`

- **Method**: `GET`
- **Response**:

    ```json
    {
        "isOK": true,
        "message": "pong"
    }
    ```