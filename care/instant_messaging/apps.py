from django.apps import AppConfig

class InstantMessagingConfig(AppConfig):
    default_auto_field = None  # We don't use database
    name = 'care.instant_messaging'
    verbose_name = 'Instant Messaging'
