# import json
# import logging
# import requests
# from django.conf import settings
# from .models import WhatsAppConfig, WhatsAppMessage
# from .message_handler import WhatsAppMessageHandler
# from datetime import datetime

# logger = logging.getLogger(__name__)

# class WhatsAppClient:
#     API_VERSION = 'v17.0'
#     BASE_URL = f'https://graph.facebook.com/{API_VERSION}'

#     def __init__(self):
#         self.config = WhatsAppConfig.objects.filter(is_active=True).first()
#         if not self.config:
#             raise ValueError("No active WhatsApp configuration found")

#         self.headers = {
#             'Authorization': f'Bearer {self.config.access_token}',
#             'Content-Type': 'application/json'
#         }

#     def send_message(self, to_number: str, message: str) -> dict:
#         """Send a text message to a WhatsApp number"""
#         endpoint = f'{self.BASE_URL}/{self.config.phone_number_id}/messages'

#         payload = {
#             "messaging_product": "whatsapp",
#             "recipient_type": "individual",
#             "to": to_number,
#             "type": "text",
#             "text": {"body": message}
#         }

#         try:
#             response = requests.post(endpoint, headers=self.headers, json=payload)
#             response.raise_for_status()
#             response_data = response.json()

#             # Store the message in our database
#             WhatsAppMessage.objects.create(
#                 message_type='OUTGOING',
#                 wa_message_id=response_data.get('messages', [{}])[0].get('id', ''),
#                 from_number=self.config.phone_number_id,
#                 to_number=to_number,
#                 message_body=message,
#                 timestamp=datetime.now(),
#                 status='sent'
#             )

#             return response_data
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Error sending WhatsApp message: {str(e)}")
#             raise

#     def verify_webhook(self, token: str) -> bool:
#         """Verify the webhook token from Meta"""
#         return token == self.config.webhook_verify_token

#     def process_webhook_event(self, data: dict) -> None:
#         """Process incoming webhook events from WhatsApp"""
#         try:
#             entry = data['entry'][0]
#             changes = entry['changes'][0]
#             value = changes['value']

#             if 'messages' in value:
#                 message = value['messages'][0]

#                 WhatsAppMessage.objects.create(
#                     message_type='INCOMING',
#                     wa_message_id=message['id'],
#                     from_number=message['from'],
#                     to_number=value['metadata']['display_phone_number'],
#                     message_body=message['text']['body'],
#                     timestamp=datetime.fromtimestamp(int(message['timestamp'])),
#                     status='received'
#                 )

#                 # TODO: Implement message handling logic here
#                 self.handle_incoming_message(message)

#         except (KeyError, IndexError) as e:
#             logger.error(f"Error processing webhook event: {str(e)}")
#             raise

#     def handle_incoming_message(self, message: dict) -> None:
#         """Handle incoming messages based on content"""
#         try:
#             from_number = message['from']
#             message_body = message['text']['body']

#             # Process the message using our handler
#             handler = WhatsAppMessageHandler(from_number)
#             response = handler.process_message(message_body)

#             # Send the response back to the user
#             self.send_message(from_number, response)
#         except Exception as e:
#             logger.error(f"Error handling message: {str(e)}")
#             # Send an error message to the user
#             self.send_message(
#                 message['from'],
#                 "Sorry, I couldn't process your request. Please try again later."
#             )


import json
import logging
import requests
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class WhatsAppClient:
    API_VERSION = settings.WHATSAPP_API_VERSION
    BASE_URL = f'https://graph.facebook.com/{API_VERSION}'

    def __init__(self):
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.verify_token = settings.WHATSAPP_VERIFY_TOKEN

        if not self.access_token:
            raise ValueError("WhatsApp Access Token is missing")

        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def send_message(self, to_number: str, message: str) -> dict:
        """Send a text message to a WhatsApp number"""
        endpoint = f'{self.BASE_URL}/{self.phone_number_id}/messages'

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
            response_data = response.json()
            logger.info(f"WhatsApp message sent successfully: {response_data}")

            return response_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            raise

    def verify_webhook(self, token: str) -> bool:
        """Verify the webhook token from Meta"""
        return token == self.verify_token

    def process_webhook_event(self, data: dict) -> None:
        """Process incoming webhook events from WhatsApp"""
        try:
            entry = data.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})

            if 'messages' in value:
                message = value['messages'][0]
                from_number = message['from']
                message_body = message['text']['body']

                # Handle incoming message
                self.handle_incoming_message(from_number, message_body)
        except (KeyError, IndexError) as e:
            logger.error(f"Error processing webhook event: {str(e)}")
            raise

    def handle_incoming_message(self, from_number: str, message_body: str) -> None:
        """Handle incoming messages based on content"""
        try:
            logger.info(f"Received message from {from_number}: {message_body}")

            # Implement your response logic here
            response = f"Received your message: {message_body}"

            # Send response
            self.send_message(from_number, response)
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            self.send_message(from_number, "Sorry, I couldn't process your request. Please try again later.")
