"""Cierre forzado de sesiones (al desactivar a alguien, cambiarle el rol o eliminar su cuenta)."""
from django.contrib.sessions.models import Session
from django.utils import timezone


def cerrar_sesiones(usuario):
    cerradas = 0
    for s in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if str(s.get_decoded().get('_auth_user_id')) == str(usuario.pk):
            s.delete()
            cerradas += 1
    return cerradas
