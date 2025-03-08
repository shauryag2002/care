import json
import logging
import requests
from django.conf import settings
from datetime import datetime
from .message_handler import WhatsAppMessageHandler

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self):
        # Use settings directly instead of database
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.webhook_verify_token = settings.WHATSAPP_VERIFY_TOKEN
        self.api_version = settings.WHATSAPP_API_VERSION
        self.base_url = f'https://graph.facebook.com/{self.api_version}'

        if not self.access_token or not self.phone_number_id:
            raise ValueError("WhatsApp configuration is incomplete. Check settings.")

        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def send_message(self, to_number: str, message: str) -> dict:
        """Send a text message to a WhatsApp number"""
        endpoint = f'{self.base_url}/{self.phone_number_id}/messages'

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            raise

    def verify_webhook(self, token: str) -> bool:
        """Verify the webhook token from Meta"""
        return token == self.webhook_verify_token

    def process_webhook_event(self, data: dict) -> None:
        """Process incoming webhook events from WhatsApp"""
        try:
            entry = data['entry'][0]
            changes = entry['changes'][0]
            value = changes['value']

            if 'messages' in value:
                message = value['messages'][0]
                self.handle_incoming_message(message)

        except (KeyError, IndexError) as e:
            logger.error(f"Error processing webhook event: {str(e)}")
            raise

    def handle_incoming_message(self, message: dict) -> None:
        """Handle incoming messages based on content"""
        try:
            from_number = message['from']
            message_body = message['text']['body']

            handler = WhatsAppMessageHandler(from_number)
            response = handler.process_message(message_body)

            self.send_message(from_number, response)
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            self.send_message(
                message['from'],
                "Sorry, I couldn't process your request. Please try again later."
            )
