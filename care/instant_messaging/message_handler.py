from django.contrib.auth import get_user_model
from care.emr.models.medication_statement import MedicationStatement
from care.emr.models.medication_administration import MedicationAdministration
from care.emr.resources.medication.request.spec import MedicationRequestStatus
from care.emr.resources.medication.statement.spec import MedicationStatementStatus
from care.emr.resources.medication.administration.spec import MedicationAdministrationStatus
from care.emr.models.patient import Patient
from care.facility.models import PatientRegistration, Facility
from care.users.models import User
import logging

logger = logging.getLogger(__name__)

class WhatsAppMessageHandler:
    def __init__(self, from_number: str):
        self.from_number = from_number
        self.user = None
        logger.info(f"Identifying user with phone number: {self.from_number}")
        self._identify_user()

    def _identify_user(self):
        """Identify if the sender is a patient or staff member"""
        try:
            logger.info(f"Identifying user with phone number: {self.from_number}")
            self.user = Patient.objects.get(phone_number=self.from_number)
            logger.info(f"Identified user: {self.user}")
        except User.DoesNotExist:
            self.user = None

    def process_message(self, message_text: str) -> str:
        """Process incoming message and return appropriate response"""
        message_text = message_text.lower().strip()

        if not self.user:
            return self._handle_unregistered_user()

        if self.user.user_type == User.TYPE_CHOICES.PATIENT:
            return self._handle_patient_request(message_text)
        else:
            return self._handle_staff_request(message_text)

    def _handle_unregistered_user(self) -> str:
        return ("Sorry, you are not registered in our system. "
                "Please visit the nearest hospital or contact support for registration.")

    def _handle_patient_request(self, message_text: str) -> str:
        """Handle requests from patients"""
        if 'records' in message_text:
            return self._get_patient_records()
        elif 'medications' in message_text:
            return self._get_current_medications()
        elif 'procedures' in message_text:
            return self._get_procedures()
        else:
            return self._get_help_message(is_patient=True)

    def _handle_staff_request(self, message_text: str) -> str:
        """Handle requests from hospital staff"""
        if 'schedule' in message_text:
            return self._get_staff_schedule()
        elif 'asset' in message_text:
            return self._get_asset_status()
        elif 'inventory' in message_text:
            return self._get_inventory_data()
        else:
            return self._get_help_message(is_patient=False)

    def _get_patient_records(self) -> str:
        try:
            patient = PatientRegistration.objects.get(phone_number=self.from_number)
            return (f"Patient ID: {patient.id}\n"
                   f"Name: {patient.name}\n"
                   f"Age: {patient.age}\n"
                   f"Last Consultation: {patient.modified_date}")
        except PatientRegistration.DoesNotExist:
            return "No patient records found."

    def _get_current_medications(self) -> str:
        """Get active medications for the patient"""
        try:
            # Get patient's registration
            patient = PatientRegistration.objects.get(phone_number=self.from_number)

            # Get active medication requests
            active_medications = MedicationRequest.objects.filter(
                patient=patient,
                status=MedicationRequestStatus.active.value
            ).select_related('encounter', 'created_by')

            if not active_medications:
                return "You don't have any active medications at this time."

            response = "🏥 *Your Current Medications:*\n\n"
            for med in active_medications:
                dosage_info = f" • {med.medication.get('display', 'Unknown Medication')}\n"
                if med.dosage_instruction:
                    for instruction in med.dosage_instruction:
                        if instruction.get('text'):
                            dosage_info += f"   - {instruction['text']}\n"
                prescribed_by = med.created_by.get_full_name() if med.created_by else "Unknown"
                dosage_info += f"   - Prescribed by: Dr. {prescribed_by}\n"
                response += dosage_info + "\n"

            return response
        except PatientRegistration.DoesNotExist:
            return "🚫 Error: Could not find your patient records. Please contact support."
        except Exception as e:
            return f"Sorry, I couldn't retrieve your medications. Error: {str(e)}"

    def _get_procedures(self) -> str:
        """Get recent and upcoming procedures for the patient"""
        try:
            patient = PatientRegistration.objects.get(phone_number=self.from_number)

            # Get recent procedures from encounters
            recent_encounters = patient.encounter_set.filter(
                encounter_type="procedure",
                discharge_date__gte=timezone.now() - timezone.timedelta(days=30)
            ).select_related('created_by')

            if not recent_encounters:
                return "No recent or upcoming procedures found."

            response = "📋 *Your Procedures:*\n\n"
            response += "*Recent Procedures:*\n"

            for encounter in recent_encounters:
                date = encounter.admission_date.strftime("%d %b %Y")
                doctor = encounter.created_by.get_full_name() if encounter.created_by else "Unknown"
                response += f" • {date}: {encounter.symptoms_text or 'Procedure'}\n"
                response += f"   - By: Dr. {doctor}\n"
                if encounter.diagnosis:
                    response += f"   - Notes: {encounter.diagnosis}\n"
                response += "\n"

            return response
        except PatientRegistration.DoesNotExist:
            return "🚫 Error: Could not find your patient records. Please contact support."
        except Exception as e:
            return f"Sorry, I couldn't retrieve your procedures. Error: {str(e)}"

    def _get_staff_schedule(self) -> str:
        """Get staff schedule information"""
        try:
            if not self.user :
                return "Error: You don't have permission to view staff schedules."
            # Get user's current facility
            facility_user = self.user.currentfacilityuser_set.first()
            if not facility_user:
                return "Error: You're not associated with any facility."

            facility = facility_user.facility
            staff = facility.users.filter(
                is_active=True
            ).select_related('user')

            response = f"👥 *Staff Schedule at {facility.name}*\n\n"

            for staff_member in staff:
                user = staff_member.user
                role = staff_member.get_role_display()
                response += f"*{user.get_full_name()}*\n"
                response += f" • Role: {role}\n"
                if hasattr(staff_member, 'shift'):
                    response += f" • Shift: {staff_member.shift}\n"
                response += "\n"

            return response
        except Exception as e:
            return f"Sorry, I couldn't retrieve the staff schedule. Error: {str(e)}"

    def _get_asset_status(self) -> str:
        """Get status of medical assets and equipment"""
        try:
            if not self.user:
                return "Error: You don't have permission to view asset status."
            logger.info(f"user is here: {self.user}")
            facility_user = self.user.currentfacilityuser_set.first()
            if not facility_user:
                return "Error: You're not associated with any facility."

            facility = facility_user.facility

            # Get facility resources and capacities
            response = f"📊 *Asset Status at {facility.name}*\n\n"

            # Bed capacity
            response += "*Bed Availability:*\n"
            response += f" • Total Beds: {facility.total_bed_capacity or 0}\n"
            response += f" • Available Beds: {facility.current_bed_capacity or 0}\n\n"

            # Equipment status
            response += "*Equipment Status:*\n"
            if hasattr(facility, 'equipments'):
                for equipment in facility.equipments.all():
                    response += f" • {equipment.name}: {equipment.count} units\n"
                    if equipment.notes:
                        response += f"   - Note: {equipment.notes}\n"

            return response
        except Exception as e:
            return f"Sorry, I couldn't retrieve the asset status. Error: {str(e)}"


    def _get_inventory_data(self) -> str:
        """Get inventory information"""
        try:
            if not self.user or not hasattr(self.user, 'currentfacilityuser_set'):
                return "Error: You don't have permission to view inventory data."

            facility_user = self.user.currentfacilityuser_set.first()
            if not facility_user:
                return "Error: You're not associated with any facility."

            facility = facility_user.facility

            response = f"📦 *Inventory Status at {facility.name}*\n\n"

            # Medication inventory
            response += "*Medicine Stock:*\n"
            if hasattr(facility, 'inventory_items'):
                med_items = facility.inventory_items.filter(item_type='MEDICINE')
                for item in med_items:
                    status = "Low" if item.quantity < item.min_quantity else "Adequate"
                    response += f" • {item.name}\n"
                    response += f"   - Stock: {item.quantity} {item.unit}\n"
                    response += f"   - Status: {status}\n"

            # Supply inventory
            response += "\n*Supply Stock:*\n"
            if hasattr(facility, 'inventory_items'):
                supply_items = facility.inventory_items.filter(item_type='SUPPLY')
                for item in supply_items:
                    status = "Low" if item.quantity < item.min_quantity else "Adequate"
                    response += f" • {item.name}\n"
                    response += f"   - Stock: {item.quantity} {item.unit}\n"
                    response += f"   - Status: {status}\n"

            return response
        except Exception as e:
            return f"Sorry, I couldn't retrieve the inventory data. Error: {str(e)}"

    def _get_help_message(self, is_patient: bool) -> str:
        if is_patient:
            return ("Available commands:\n"
                   "- 'records' - View your patient records\n"
                   "- 'medications' - View current medications\n"
                   "- 'procedures' - View procedures")
        else:
            return ("Available commands:\n"
                   "- 'schedule' - View your schedule\n"
                   "- 'asset' - Check asset status\n"
                   "- 'inventory' - Check inventory data")
