from django.core.exceptions import PermissionDenied
from care.models import Patient
from .models import PatientOTP

def get_patient_data(phone, otp):
    try:
        otp_obj = PatientOTP.objects.get(phone=phone, otp=otp, is_verified=False)
        otp_obj.is_verified = True
        otp_obj.save()
        patient = Patient.objects.get(phone=phone)
        return {
            "medications": patient.current_medications,
            "procedures": patient.procedures
        }
    except PatientOTP.DoesNotExist:
        raise PermissionDenied("Invalid OTP")

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

class StaffScheduleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        schedule = user.schedule_set.all()  # Assuming a Schedule model exists
        return Response(schedule)

def handle_whatsapp_message(data):
    message = data["entry"][0]["changes"][0]["value"]["messages"][0]
    phone = message["from"]
    text = message["text"]["body"]

    if text.startswith("OTP"):
        # Generate and send OTP via WhatsApp
        otp = generate_otp()
        PatientOTP.objects.update_or_create(phone=phone, defaults={"otp": otp})
        send_whatsapp_text(phone, f"Your OTP is: {otp}")
    elif text.startswith("MEDS"):
        # Fetch medications after OTP verification
        _, otp = text.split()
        data = get_patient_data(phone, otp)
        send_whatsapp_text(phone, f"Medications: {data['medications']}")
