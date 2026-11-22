from django.apps import AppConfig


class QrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.qr'
    label = 'qr'
    verbose_name = 'Códigos QR'
