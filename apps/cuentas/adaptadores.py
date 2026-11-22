"""Adaptadores de django-allauth: reglas de EcoParce para el ingreso con correo y con Google.

Misma lógica que CiudadReporta: registro con correo + contraseña y verificación real del correo
con un código de 6 caracteres, o ingreso con Google verificando el token (firma, emisor, audiencia
y correo verificado). Las cuentas nuevas siempre nacen como VISITANTE."""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from apps.core.seguridad import evento

from .models import Rol


def _destino(request, usuario):
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()},
                                                   require_https=request.is_secure()):
        return destino
    if getattr(usuario, 'es_personal', False):
        return reverse('estadisticas:resumen')
    return reverse('cuentas:mi_cuenta')


class CuentaAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return True

    def new_user(self, request):
        usuario = super().new_user(request)
        usuario.rol = Rol.VISITANTE  # nunca se obtiene un rol administrativo registrándose
        return usuario

    def clean_email(self, email):
        from django import forms
        from django.conf import settings

        from .forms import dominio_recibe_correo
        correo = super().clean_email(email).strip().lower()
        if settings.VERIFICAR_MX_CORREO and not dominio_recibe_correo(correo):
            raise forms.ValidationError('Ese dominio de correo no existe o no recibe mensajes. Revisa que esté bien escrito.')
        return correo

    def get_login_redirect_url(self, request):
        return _destino(request, request.user)

    def get_logout_redirect_url(self, request):
        return '/'

    def is_reauthentication_required(self, *, app, **kwargs):
        """Un ingreso completo de hace menos de 5 minutos cuenta como identidad confirmada.
        Pasado ese tiempo, las acciones sensibles piden de nuevo el código TOTP o la contraseña."""
        import time

        from allauth.account.authentication import get_authentication_records
        from allauth.core import context
        from django.conf import settings
        request = context.request
        if request is not None and request.user.is_authenticated:
            registros = get_authentication_records(request, request.user)
            if registros and time.time() - registros[-1].get('at', 0) < settings.ACCOUNT_REAUTHENTICATION_TIMEOUT:
                return False
        return super().is_reauthentication_required(app=app, **kwargs)

    def send_mail(self, template_prefix, email, context):
        evento('correo_enviado', plantilla=template_prefix.rsplit('/', 1)[-1])
        return super().send_mail(template_prefix, email, context)


class GoogleAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        datos = sociallogin.account.extra_data or {}
        verificado = datos.get('email_verified', datos.get('verified_email'))
        if str(verificado).lower() not in ('true', '1'):
            evento('google_correo_no_verificado', request)
            messages.error(request, 'Tu cuenta de Google no tiene el correo verificado. Verifícalo en Google y vuelve a intentar.')
            raise ImmediateHttpResponse(redirect('account_login'))
        # El «secuestro previo de cuenta» (alguien registra el correo de otra persona sin verificarlo)
        # lo neutraliza allauth: al enlazar Google borra la contraseña de esa cuenta no verificada.

    def populate_user(self, request, sociallogin, data):
        usuario = super().populate_user(request, sociallogin, data)
        datos = sociallogin.account.extra_data or {}
        usuario.correo = (datos.get('email') or data.get('email') or '').strip().lower()
        nombre = datos.get('name') or ' '.join(x for x in [data.get('first_name'), data.get('last_name')] if x)
        usuario.nombre = (nombre or usuario.correo.split('@')[0])[:120]
        usuario.rol = Rol.VISITANTE
        return usuario

    def save_user(self, request, sociallogin, form=None):
        usuario = super().save_user(request, sociallogin, form)
        usuario.set_unusable_password()
        usuario.save(update_fields=['password'])
        evento('cuenta_creada_google', request, usuario)
        return usuario
