from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from care.facility.models import PatientRegistration, Facility
from care.users.models import User
from care.emr.models import Patient
from care.emr.models.medication_request import MedicationRequest
from care.emr.models.medication_statement import MedicationStatement
from care.emr.models.medication_administration import MedicationAdministration
from care.emr.resources.medication.request.spec import MedicationRequestStatus
from care.emr.resources.medication.statement.spec import MedicationStatementStatus
from care.emr.resources.medication.administration.spec import MedicationAdministrationStatus
from .templates import MessageTemplates
from care.instant_messaging.whatsapp_client import WhatsAppClient
import logging

logger = logging.getLogger(__name__)

class WhatsAppMessageHandler:
    def __init__(self, from_number: str):
        self.from_number = from_number
        self.user = None
        self.patient = None
        self._identify_user()
        self.templates = MessageTemplates()
        self.whatsapp_client = WhatsAppClient()

    def _identify_user(self):
        """Identify if the sender is a patient or staff member"""
        try:
            logger.info(f"Identifying user with phone number: {self.from_number}")

            # Normalize phone number
            normalized_number = self.from_number.strip().replace(" ", "")
            if not normalized_number.startswith('+'):
                if normalized_number.startswith('91') and len(normalized_number) >= 12:
                    normalized_number = f"+{normalized_number}"
                elif len(normalized_number) == 10:
                    normalized_number = f"+91{normalized_number}"
                else:
                    normalized_number = f"+{normalized_number}"

            logger.info(f"Looking up user/patient with normalized number: {normalized_number}")

            # First try to find a patient record
            try:
                self.patient = Patient.objects.filter(
                    phone_number=normalized_number
                ).order_by('-modified_date').first()
                logger.info(f"Found patient: {self.patient}")
                return;
            except Patient.DoesNotExist:
                # If no patient found, try emergency contact
                self.patient = Patient.objects.filter(
                    emergency_phone_number=normalized_number
                ).first()
                if self.patient:
                    logger.info(f"Found patient via emergency contact: {self.patient}")
                    return;

            # Then try to find a staff user
            try:
                self.user = User.objects.get(phone_number=normalized_number)
                logger.info(f"Found staff user: {self.user}")
            except User.DoesNotExist:
                try:
                    self.user = User.objects.get(alt_phone_number=normalized_number)
                    logger.info(f"Found staff user via alternate number: {self.user}")
                except User.DoesNotExist:
                    if self.patient:
                        # If we found a patient but no staff user, create a basic user for the patient
                        self.user = User.objects.filter(
                            phone_number=normalized_number
                        ).first()
                        if not self.user:
                            logger.info(f"Creating new user for patient: {self.patient}")
                            self.user = User.objects.create(
                                phone_number=normalized_number,
                                username=f"patient_{self.patient.external_id}",
                                first_name=self.patient.name,
                                is_active=True,
                                verified=True
                            )

            logger.info(f"Identified user: {self.user}, patient: {self.patient}")
        except Exception as e:
            logger.error(f"Error in user identification: {str(e)}")
            self.user = None
            self.patient = None

    def process_message(self, message_text: str) -> str:
        """Process incoming message and return appropriate response"""
        message_text = message_text.lower().strip()

        if message_text == 'help':
            return self.templates.help_message(
                # Show patient menu if we found a patient record
                is_patient=bool(self.patient or (self.user and not self.user.is_staff))
            )

        if not (self.user or self.patient):
            return self._handle_unregistered_user()

        # Handle patient requests if we found a patient record or non-staff user
        if self.patient or (self.user and not self.user.is_staff):
            return self._handle_patient_request(message_text)
        else:
            return self._handle_staff_request(message_text)

    def _handle_unregistered_user(self) -> str:
        support_email = "support@care.ohc.network"
        helpline = "1800-123-456"  # You can update this with your actual helpline number

        languages = {
            'en': 'English',
            'ml': 'Malayalam',
            'hi': 'Hindi',
            'ta': 'Tamil'
        }

        lang_support = "\n".join([f"   • {name}" for code, name in languages.items()])

        return (
            "🏥 *You are not registered in our system*\n\n"
            "*How to Register:*\n\n"
            "1️⃣ *Visit a Hospital*\n"
            "   • Find your nearest CARE-registered hospital\n"
            "   • Registration is available during OPD hours\n\n"
            "2️⃣ *Required Documents*\n"
            "   • Valid ID (Aadhaar/PAN/Passport)\n"
            "   • Address proof\n"
            "   • Recent photograph\n"
            "   • Previous medical records (if any)\n\n"
            "3️⃣ *At Registration Desk*\n"
            "   • Fill patient registration form\n"
            "   • Provide this WhatsApp number\n"
            "   • Get your Patient ID\n\n"
            "4️⃣ *Need Help?*\n"
            f"   • Call: {helpline} (24x7 Toll-free)\n"
            f"   • Email: {support_email}\n"
            "   • Available in:\n"
            f"{lang_support}\n\n"
            "*After Registration You Can:*\n"
            "✓ View medical records\n"
            "✓ Check appointments\n"
            "✓ Get medication reminders\n"
            "✓ Receive important updates\n\n"
            "Type 'help' anytime to see available commands."
        )

    def _handle_patient_request(self, message_text: str) -> str:
        """Handle requests from patients"""
        if 'records' in message_text:
            return self._get_patient_records()
        elif 'medications' in message_text:
            return self._get_current_medications()
        elif 'procedures' in message_text:
            return self._get_procedures()
        else:
            return self.templates.help_message(is_patient=True)

    def _handle_staff_request(self, message_text: str) -> str:
        """Handle requests from hospital staff"""
        if 'schedule' in message_text:
            return self._get_staff_schedule()
        elif 'asset' in message_text:
            return self._get_asset_status()
        elif 'inventory' in message_text:
            return self._get_inventory_data()
        else:
            return self.templates.help_message(is_patient=False)

    def _get_patient_records(self) -> str:
        """Get patient records"""
        try:
            if not self.patient:
                return "No patient records found. Please visit a facility to register."

            # Format the last visit date nicely
            last_visit_date = self.patient.modified_date
            formatted_date = last_visit_date.strftime("%d %B, %Y") if last_visit_date else 'Not Available'

            return self.templates.patient_record({
                'id': self.patient.id,
                'name': self.patient.name,
                'age': self.patient.get_age(),
                'gender': self.patient.gender,
                'blood_group': self.patient.blood_group or 'Not Available',
                'last_visit': formatted_date
            })
        except Exception as e:
            logger.error(f"Error getting patient records: {str(e)}")
            return "Sorry, I couldn't retrieve your records. Please try again later."

    def _get_current_medications(self) -> str:
        """Get active medications for the patient"""
        try:
            logger.info(f"selft.patient: {self.patient}")
            # Get patient's registration
            if not self.patient:
                return "No patient records found. Please visit a facility to register."

            # Get active medication requests
            active_medications = MedicationRequest.objects.filter(
                patient=self.patient,
                status=MedicationRequestStatus.active.value
            ).select_related('encounter', 'created_by')

            if not active_medications:
                return "You don't have any active medications at this time."

            response = "🏥 *Your Current Medications:*\n\n"
            for med in active_medications:
                med_name = med.medication.get('display', 'Unknown Medication')
                response += f" • *{med_name}*\n"

                # Extract dosage
                dosage = med.medication.get('dosage')
                if dosage:
                    response += f"   - Dosage: {dosage}\n"

                # Extract frequency and instructions from dosage_instruction
                if med.dosage_instruction:
                    for instruction in med.dosage_instruction:
                        # Get frequency
                        if instruction.get('timing', {}).get('code', {}).get('text'):
                            response += f"   - Frequency: {instruction['timing']['code']['text']}\n"

                        # Get duration
                        if instruction.get('timing', {}).get('duration'):
                            duration = instruction['timing']['duration']
                            duration_unit = instruction['timing'].get('durationUnit', 'days')
                            response += f"   - Duration: {duration} {duration_unit}\n"

                        # Get instructions
                        if instruction.get('text'):
                            response += f"   - Instructions: {instruction['text']}\n"

                # Add prescriber information
                prescribed_by = med.created_by.get_full_name() if med.created_by else "Unknown"
                response += f"   - Prescribed by: Dr. {prescribed_by}\n\n"

            return response
        except Exception as e:
            logger.error(f"Error getting medications: {str(e)}")
            return "Sorry, I couldn't retrieve your medications. Please try again later."

    def _get_procedures(self) -> str:
        """Get recent and upcoming procedures for the patient"""
        try:
            if not self.patient:
                return "🚫 Error: Could not find your patient records. Please contact support."

            from care.emr.models import Encounter
            from django.utils import timezone
            from datetime import timedelta

            # Get recent procedures from encounters - last 30 days
            recent_encounters = Encounter.objects.filter(
                patient=self.patient,
                # encounter_class="procedure",
                # admission_date__gte=timezone.now() - timedelta(days=30)
            )
            # .select_related(
            #     'created_by',
            #     'facility'
            # ).order_by('-admission_date')
            logger.info(f"recent_encounters: {recent_encounters}")
            if not recent_encounters:
                upcoming_encounters = Encounter.objects.filter(
                    patient=self.patient,
                    # encounter_class="procedure",
                    # admission_date__gt=timezone.now()
                )
                # .select_related(
                #     'created_by',
                #     'facility'
                # ).order_by('admission_date')

                if not upcoming_encounters:
                    return "No recent or upcoming procedures found."

                response = "📋 *Your Procedures:*\n\n"
                response += "*Upcoming Procedures:*\n"

                for encounter in upcoming_encounters:
                    date = encounter.created_date.strftime("%d %b %Y")
                    doctor = encounter.created_by.get_full_name() if encounter.created_by else "Unknown"
                    facility = encounter.facility.name if encounter.facility else "Unknown Facility"

                    response += f" • {date}: {encounter.encounter_class or 'Procedure'}\n"
                    response += f"   - At: {facility}\n"
                    response += f"   - By: Dr. {doctor}\n"
                    if encounter.status:
                        response += f"   - Reason: {encounter.status}\n"
                    response += "\n"

                return response

            response = "📋 *Your Procedures:*\n\n"
            response += "*Recent Procedures:*\n"

            for encounter in recent_encounters:
                date = encounter.created_date.strftime("%d %b %Y")
                doctor = encounter.created_by.get_full_name() if encounter.created_by else "Unknown"
                facility = encounter.facility.name if encounter.facility else "Unknown Facility"

                response += f" • {date}: {encounter.encounter_class or 'Procedure'}\n"
                response += f"   - At: {facility}\n"
                response += f"   - By: Dr. {doctor}\n"
                if encounter.status:
                    response += f"   - Reason: {encounter.status}\n"
                if encounter.created_date:
                    discharge = encounter.created_date.strftime("%d %b %Y")
                    response += f"   - Discharged: {discharge}\n"
                response += "\n"

            # Check if there are any upcoming procedures
            upcoming_encounters = Encounter.objects.filter(
                patient=self.patient,
                # encounter_class="procedure",
                # admission_date__gt=timezone.now()
            )
            # .select_related(
            #     'created_by',
            #     'facility'
            # ).order_by('admission_date')

            if upcoming_encounters:
                response += "*Upcoming Procedures:*\n"
                for encounter in upcoming_encounters:
                    date = encounter.created_date.strftime("%d %b %Y")
                    doctor = encounter.created_by.get_full_name() if encounter.created_by else "Unknown"
                    facility = encounter.facility.name if encounter.facility else "Unknown Facility"

                    response += f" • {date}: {encounter.encounter_class or 'Procedure'}\n"
                    response += f"   - At: {facility}\n"
                    response += f"   - By: Dr. {doctor}\n"
                    if encounter.status:
                        response += f"   - Reason: {encounter.status}\n"
                    response += "\n"

            return response
        except Exception as e:
            logger.error(f"Error getting procedures: {str(e)}")
            return f"Sorry, I couldn't retrieve your procedures. Please try again later."

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
            if not self.user :
                return "Error: You don't have permission to view asset status."
            logger.info(f"Getting staff schedule for user: {self.user.asset}")
            facility_user = self.user.currentfacilityuser_set.first()
            if not facility_user:
                return "Error: You're not associated with any facility."

            facility = facility_user.facility

            # Get facility assets
            from care.facility.models.asset import Asset, AvailabilityStatus

            assets = Asset.objects.filter(
                Q(current_location__facility=facility) |
                Q(home_facility=facility)
            ).select_related(
                'current_location',
                'current_location__facility'
            )

            if not assets:
                return f"No monitored assets found at {facility.name}"

            response = f"📊 *Asset Status at {facility.name}*\n\n"

            # Group assets by status
            status_groups = {
                AvailabilityStatus.OPERATIONAL: [],
                AvailabilityStatus.DOWN: [],
                AvailabilityStatus.UNDER_MAINTENANCE: [],
                AvailabilityStatus.NOT_MONITORED: []
            }

            for asset in assets:
                # Get latest availability record
                latest_record = asset.availability_records.order_by('-timestamp').first()
                status = latest_record.status if latest_record else AvailabilityStatus.NOT_MONITORED

                asset_info = {
                    'name': asset.name,
                    'location': asset.current_location.name if asset.current_location else 'Unknown',
                    'class': asset.asset_class,
                    'last_update': latest_record.timestamp.strftime("%d-%m-%Y %H:%M") if latest_record else 'Never'
                }
                status_groups[status].append(asset_info)

            # Format response by status
            if status_groups[AvailabilityStatus.OPERATIONAL]:
                response += "✅ *Operational Assets:*\n"
                for asset in status_groups[AvailabilityStatus.OPERATIONAL]:
                    response += f" • {asset['name']} ({asset['class']})\n"
                    response += f"   - Location: {asset['location']}\n"
                response += "\n"

            if status_groups[AvailabilityStatus.DOWN]:
                response += "❌ *Down Assets:*\n"
                for asset in status_groups[AvailabilityStatus.DOWN]:
                    response += f" • {asset['name']} ({asset['class']})\n"
                    response += f"   - Location: {asset['location']}\n"
                    response += f"   - Last Seen: {asset['last_update']}\n"
                response += "\n"

            if status_groups[AvailabilityStatus.UNDER_MAINTENANCE]:
                response += "🔧 *Under Maintenance:*\n"
                for asset in status_groups[AvailabilityStatus.UNDER_MAINTENANCE]:
                    response += f" • {asset['name']} ({asset['class']})\n"
                    response += f"   - Location: {asset['location']}\n"
                response += "\n"

            # Add bed capacity if available
            if hasattr(facility, 'total_bed_capacity') and hasattr(facility, 'current_bed_capacity'):
                response += "*Bed Availability:*\n"
                response += f" • Total Beds: {facility.total_bed_capacity or 0}\n"
                response += f" • Available Beds: {facility.current_bed_capacity or 0}\n"

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
    def send_whatsapp_message(self,to_number:str, message: str) -> dict:
        """Send a text message to a WhatsApp number"""
        response = self.process_message(message)
        self.whatsapp_client.send_message(to_number, response)
