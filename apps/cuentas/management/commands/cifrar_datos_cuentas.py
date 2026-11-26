"""Cifra de forma idempotente los campos sensibles de cuentas existentes y actualiza correo_hash."""
from django.core.management.base import BaseCommand
from django.db import connection

from apps.core.cifrado import cifrar_texto, esta_cifrado, indice_ciego
from apps.core.rls import contexto_rls_sistema
from apps.cuentas.models import SolicitudAdmin, Usuario


class Command(BaseCommand):
    help = 'Cifra en base de datos los registros heredados de cuentas y solicitudes de administrador.'

    def handle(self, *args, **options):
        with contexto_rls_sistema():
            self._cifrar()

    def _cifrar(self):
        usuarios_actualizados = 0
        with connection.cursor() as cur:
            cur.execute('SELECT id, correo, nombre, correo_hash FROM usuario')
            filas = cur.fetchall()
        for pk, correo, nombre_raw, hash_actual in filas:
            nuevo_hash = indice_ciego(correo, contexto='correo')
            necesita_nombre = bool(nombre_raw) and not esta_cifrado(nombre_raw)
            necesita_hash = hash_actual != nuevo_hash
            if necesita_nombre or necesita_hash:
                u = Usuario.objects.get(pk=pk)
                u.save(update_fields=['nombre', 'correo_hash'])
                usuarios_actualizados += 1

        solicitudes_actualizadas = 0
        with connection.cursor() as cur:
            cur.execute('SELECT id, motivo FROM solicitud_admin')
            filas_sol = cur.fetchall()
        for pk, motivo_raw in filas_sol:
            if motivo_raw and not esta_cifrado(motivo_raw):
                s = SolicitudAdmin.objects.get(pk=pk)
                s.motivo = cifrar_texto(motivo_raw)
                s.save(update_fields=['motivo'])
                solicitudes_actualizadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Cifrado verificado. Usuarios actualizados: {usuarios_actualizados}; '
                f'solicitudes actualizadas: {solicitudes_actualizadas}.'
            )
        )
