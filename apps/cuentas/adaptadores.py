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
    """Calcula la redirección segura tras ingresar o registrarse según el rol real del usuario."""
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()},
                                                   require_https=request.is_secure()):
        # Nunca enviar a un visitante al panel administrativo tras registrarse o ingresar
        if destino.startswith('/panel/') and not getattr(usuario, 'es_personal', False):
            return reverse('cuentas:mi_cuenta')
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

    def is_safe_url(self, url):
        """Impide que un visitante sea redirigido a /panel/ tras registrarse o iniciar sesión."""
        if not super().is_safe_url(url):
            return False
        from allauth.core import context as allauth_ctx
        req = getattr(allauth_ctx, 'request', None)
        if url and str(url).startswith('/panel/') and req is not None:
            if req.path.startswith('/accounts/signup'):
                return False
            usuario = getattr(req, 'user', None)
            if usuario is not None and getattr(usuario, 'is_authenticated', False) and not getattr(usuario, 'es_personal', False):
                return False
        return True

    def get_login_redirect_url(self, request):
        return _destino(request, request.user)

    def get_signup_redirect_url(self, request):
        return _destino(request, request.user)

    def get_logout_redirect_url(self, request):
        messages.info(request, 'Cerraste sesión de forma segura.')
        return reverse('account_login')

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
        import logging

        from allauth.core import context as allauth_ctx
        from django.conf import settings
        plantilla = template_prefix.rsplit('/', 1)[-1]
        evento('correo_enviado', plantilla=plantilla)
        try:
            res = super().send_mail(template_prefix, email, context)
        except Exception as exc:  # pragma: no cover
            logging.getLogger('ecoparce').error('Error enviando correo (%s): %s', plantilla, exc)
            req = getattr(allauth_ctx, 'request', None)
            if req is not None:
                messages.error(req, 'No pudimos enviar el correo de verificación ahora mismo. Revisa la configuración SMTP o inténtalo de nuevo.')
            return None
        # En desarrollo local sin SMTP real, mostrar el código en pantalla con un mensaje limpio.
        if (settings.DEBUG
                and settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
                and context.get('code')):
            req = getattr(allauth_ctx, 'request', None)
            if req is not None:
                messages.info(req, f"Tu código de verificación es {context['code']}. Ingrésalo abajo para continuar.")
        return res


class GoogleAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        import logging
        detalle = repr(exception) if exception is not None else str(error or 'desconocido')
        logging.getLogger('ecoparce').warning('Google OAuth error (%s): %s', error, detalle)
        evento('google_error_autenticacion', request, error=str(error or 'desconocido'), detalle=detalle[:180])
        messages.error(
            request,
            'No se pudo completar el ingreso con Google. Verifica que tu correo esté autorizado en Google Cloud y vuelve a intentarlo.',
        )
        raise ImmediateHttpResponse(redirect('account_login'))

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
