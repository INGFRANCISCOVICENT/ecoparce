"""Inicializa de forma idempotente el administrador principal y el contenido educativo en producción."""
import os
import secrets

from allauth.account.models import EmailAddress
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.core.rls import contexto_rls_sistema
from apps.cuentas.models import Rol, Usuario


class Command(BaseCommand):
    help = 'Crea/actualiza el administrador principal y carga guías, residuos y trivia si están vacíos (idempotente).'

    def handle(self, *args, **options):
        with contexto_rls_sistema():
            self._ejecutar()

    def _ejecutar(self):
        correo_principal = os.environ.get('ADMIN_PRINCIPAL_CORREO', 'fjnv1305@gmail.com').strip().lower()
        clave_inicial = os.environ.get('ADMIN_PRINCIPAL_CLAVE', '').strip()

        u_sys, creado = Usuario.objects.get_or_create(
            correo=correo_principal,
            defaults={'nombre': 'Francisco Navarro Vicent', 'rol': Rol.SISTEMA, 'is_active': True},
        )
        if creado:
            if clave_inicial:
                u_sys.set_password(clave_inicial)
            else:
                u_sys.set_unusable_password()
            u_sys.save()
        elif u_sys.rol != Rol.SISTEMA:
            u_sys.rol = Rol.SISTEMA
            u_sys.save(update_fields=['rol'])
        EmailAddress.objects.update_or_create(user=u_sys, email=correo_principal, defaults={'verified': True, 'primary': True})

        # Dos cuentas editoriales base para cumplir RN-03 (autor != revisor) al cargar contenido inicial oficial
        for correo, nombre in [
            ('danixa@ecoparce.com.co', 'Danixa Herrera'),
            ('darien@ecoparce.com.co', 'Darien García'),
        ]:
            ed, ed_creado = Usuario.objects.get_or_create(
                correo=correo,
                defaults={'nombre': nombre, 'rol': Rol.CONTENIDO, 'is_active': True},
            )
            if ed_creado:
                ed.set_password(secrets.token_urlsafe(24))
                ed.save()
            EmailAddress.objects.update_or_create(user=ed, email=correo, defaults={'verified': True, 'primary': True})

        call_command('cargar_contenido_inicial', autor='danixa@ecoparce.com.co', revisor='darien@ecoparce.com.co', demo=True)
        self.stdout.write(self.style.SUCCESS(f'Producción inicializada correctamente. Admin principal: {correo_principal}'))
