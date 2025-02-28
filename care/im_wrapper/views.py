import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from .services import verify_whatsapp_webhook, handle_whatsapp_message, handle_telegram_message

@csrf_exempt
def whatsapp_webhook(request):
    # Verify webhook (Meta sends a challenge on setup)
    if request.method == "GET":
        challenge = verify_whatsapp_webhook(request)
        return JsonResponse({"status": "ok", "challenge": challenge})
    
    # Handle incoming messages
    elif request.method == "POST":
        data = json.loads(request.body)
        handle_whatsapp_message(data)
        return JsonResponse({"status": "success"})

@csrf_exempt
def telegram_webhook(request):
    data = json.loads(request.body)
    handle_telegram_message(data)
    return JsonResponse({"status": "success"})
