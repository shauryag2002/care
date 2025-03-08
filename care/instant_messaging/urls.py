from django.urls import path
from .api.viewsets.webhook import WhatsAppWebhookViewSet

# Direct mapping for webhook endpoint
webhook_view = WhatsAppWebhookViewSet.as_view({
    'get': 'webhook',
    'post': 'webhook'
})

app_name = 'instant_messaging'

urlpatterns = [
    path('webhook/', webhook_view, name='whatsapp-webhook'),
]
