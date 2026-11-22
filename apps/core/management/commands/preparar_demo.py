"""Prepara una base de datos LOCAL de demostración (nunca usar en producción).

    python manage.py preparar_demo

Crea tres administradores de prueba, carga el contenido inicial y los puntos de ejemplo.
"""
from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.cuentas.models import Rol, Usuario

CLAVE_DEMO = 'EcoParce-Demo-2026'  # nosec B105: solo para la base local de demostración
ADMINS = [('fjnv1305@gmail.com', 'Francisco Navarro Vicent', Rol.SISTEMA),
          ('francisco@ecoparce.com.co', 'Francisco Navarro', Rol.SISTEMA),
          ('danixa@ecoparce.com.co', 'Danixa Herrera', Rol.CONTENIDO),
          ('darien@ecoparce.com.co', 'Darien García', Rol.CONTENIDO)]


class Command(BaseCommand):
    help = 'Crea datos de demostración en la base local (bloqueado si DEBUG=False).'

    def handle(self, *args, **o):
        if not settings.DEBUG:
            raise CommandError('preparar_demo solo funciona en desarrollo (DEBUG=True).')
        for correo, nombre, rol in ADMINS:
            u, creado = Usuario.objects.get_or_create(correo=correo, defaults={'nombre': nombre, 'rol': rol})
            if creado:
                u.set_password(CLAVE_DEMO)
                u.save()
            elif u.rol != rol or not u.is_active:
                u.rol = rol
                u.is_active = True
                u.save(update_fields=['rol', 'is_active'])
            EmailAddress.objects.update_or_create(user=u, email=correo, defaults={'verified': True, 'primary': True})
        call_command('cargar_contenido_inicial', autor='danixa@ecoparce.com.co', revisor='darien@ecoparce.com.co', demo=True)
        self.stdout.write(self.style.SUCCESS(
            f'Demo lista. Panel: http://127.0.0.1:8000/panel/  ·  francisco@ecoparce.com.co / {CLAVE_DEMO}'))
