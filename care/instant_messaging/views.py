import json
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .whatsapp_client import WhatsAppClient
from .message_handler import WhatsAppMessageHandler
import logging
logger = logging.getLogger(__name__)
@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.whatsapp_client = WhatsAppClient()

    def get(self, request, *args, **kwargs):
        """Handle webhook verification from Meta"""
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' :
                return HttpResponse(challenge)
            return HttpResponse('Forbidden', status=403)

        return HttpResponse('Bad Request', status=400)

    def post(self, request, *args, **kwargs):
        """Handle incoming messages and events"""
        try:
            logger.info(f"WhatsApp webhook event: {request.body}")
            data = json.loads(request.body.decode('utf-8'))
            self.whatsapp_client.process_webhook_event(data)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
