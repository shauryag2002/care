from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import EMRModelViewSet, EMRQuestionnaireResponseMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.medication.request.spec import (
    MedicationRequestReadSpec,
    MedicationRequestSpec,
    MedicationRequestUpdateSpec,
)
from care.emr.resources.questionnaire.spec import SubjectType
from care.security.authorization import AuthorizationController
from care.users.models import User
# from care.utils.whatsapp.message_handler import WhatsAppMessageHandler
import logging
logger = logging.getLogger(__name__)


class StatusFilter(filters.CharFilter):
    def filter(self, qs, value):
        if value:
            statuses = value.split(",")
            return qs.filter(status__in=statuses)
        return qs


class MedicationRequestFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    status = StatusFilter()
    name = filters.CharFilter(field_name="medication__display", lookup_expr="icontains")


class MedicationRequestViewSet(
    EncounterBasedAuthorizationBase, EMRQuestionnaireResponseMixin, EMRModelViewSet
):
    database_model = MedicationRequest
    pydantic_model = MedicationRequestSpec
    pydantic_read_model = MedicationRequestReadSpec
    pydantic_update_model = MedicationRequestUpdateSpec
    questionnaire_type = "medication_request"
    questionnaire_title = "Medication Request"
    questionnaire_description = "Medication Request"
    questionnaire_subject_type = SubjectType.patient.value
    filterset_class = MedicationRequestFilter
    filter_backends = [filters.DjangoFilterBackend]
    # whatsapp_client = WhatsAppMessageHandler("919971439246")

    def get_queryset(self):
        self.authorize_read_encounter()
        return (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "created_by", "updated_by")
        )

    def authorize_create(self, instance):
        super().authorize_create(instance)
        if instance.requester:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)
            requester = get_object_or_404(User, external_id=instance.requester)
            if not AuthorizationController.call(
                "can_update_encounter_obj", requester, encounter
            ):
                raise PermissionDenied(
                    "Requester does not have permission to update encounter"
                )

    # def perform_create(self, serializer):
    #     # instance = serializer.save()
    #     self.whatsapp_client.send_whatsapp_message(
    #         message="medications"
    #         )
    #     instance = super().perform_create(serializer)
    #     # self._send_whatsapp_notification(instance)
    #     return instance

    # def perform_update(self,request, *args,**kwargs):
    #     # instance = serializer.save()
    #     logger.info(f"phonyy {request.user.phone_number}")
    #     instance = super().perform_update(request, *args, **kwargs)
    #     logger.info(f"Medication Request Updated: {instance}")
    #     # self.whatsapp_client.send_whatsapp_message(
    #     #     message="medications"
    #     #     )
    #     # self._send_whatsapp_notification(instance)
    #     return instance

    # def _send_whatsapp_notification(self, instance):
    #     try:
    #         whatsapp_client = WhatsAppWebhookView()
    #         if instance.patient and instance.patient.phone_number:
    #             whatsapp_client.send_whatsapp_message(
    #                 to_number=instance.patient.phone_number,
    #                 message="medications"
    #             )
    #     except Exception as e:
    #         # Log the error but don't interrupt the main flow
    #         print(f"WhatsApp notification error: {e}")


InternalQuestionnaireRegistry.register(MedicationRequestViewSet)
