"""Auditoría y registro de eventos de autenticación (OWASP A09)."""
from allauth.account.internal.flows.login import record_authentication
from allauth.mfa.signals import authenticator_added, authenticator_removed, authenticator_reset
from allauth.socialaccount.signals import social_account_added, social_account_removed
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core.seguridad import evento


@receiver(user_logged_in)
def auditar_ingreso(sender, request, user, **kwargs):
    evento('login_ok', request, user, rol=user.rol)
    if user.es_personal:
        RegistroAuditoria.registrar(user, Accion.INGRESO, user, 'Ingreso al panel')


@receiver(user_logged_out)
def auditar_salida(sender, request, user, **kwargs):
    if user is not None:
        evento('logout', request, user)


@receiver(user_login_failed)
def auditar_fallo(sender, credentials, request=None, **kwargs):
    evento('login_fallido', request)


@receiver(authenticator_added)
def mfa_activada(sender, request, user, authenticator, **kwargs):
    # Quien acaba de activar TOTP demostró poseer el segundo factor en esta sesión.
    record_authentication(request, user, 'mfa', id=authenticator.pk, type=authenticator.type)
    evento('mfa_activada', request, user, tipo=authenticator.type)
    if user.es_personal:
        RegistroAuditoria.registrar(user, Accion.ACTIVAR, user, f'Activó la verificación en dos pasos ({authenticator.type})')


@receiver(authenticator_removed)
def mfa_desactivada(sender, request, user, authenticator, **kwargs):
    evento('mfa_desactivada', request, user, tipo=authenticator.type)
    if user.es_personal:
        RegistroAuditoria.registrar(user, Accion.DESACTIVAR, user, f'Desactivó la verificación en dos pasos ({authenticator.type})')


@receiver(authenticator_reset)
def mfa_codigos(sender, request, user, authenticator, **kwargs):
    evento('mfa_codigos_regenerados', request, user)


@receiver(social_account_added)
def google_enlazado(sender, request, sociallogin, **kwargs):
    evento('google_enlazado', request, sociallogin.user)


@receiver(social_account_removed)
def google_desenlazado(sender, request, socialaccount, **kwargs):
    evento('google_desenlazado', request, socialaccount.user)


from allauth.mfa.signals import authentication_failed  # noqa: E402


@receiver(authentication_failed)
def mfa_fallida(sender, request, user, **kwargs):
    evento('mfa_codigo_incorrecto', request, user)
