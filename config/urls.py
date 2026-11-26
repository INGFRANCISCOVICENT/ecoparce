from django.conf import settings
from django.conf.urls.static import static
from django.http import Http404
from django.urls import include, path, re_path

from apps.api.views import oauth_metadata
from apps.core.context_processors import google_configurado
from apps.core.views import security_txt


def _desactivada(request, *args, **kwargs):
    raise Http404


# Flujos de allauth que EcoParce no usa: cada cuenta tiene un único correo, que no se cambia.
BLOQUEADAS = [
    re_path(r'^accounts/email/', _desactivada),
]

def _google_login(request, *args, **kwargs):
    """Evita el error 400 de Google («Missing required parameter: client_id») cuando faltan las credenciales."""
    from allauth.socialaccount.providers.google.views import oauth2_login
    from django.contrib import messages
    from django.shortcuts import redirect
    if not google_configurado():
        messages.error(request, 'El ingreso con Google aún no está configurado en este servidor. Usa tu correo y contraseña.')
        return redirect('account_login')
    return oauth2_login(request, *args, **kwargs)


BLOQUEADAS.append(re_path(r'^accounts/google/login/$', _google_login))

urlpatterns = BLOQUEADAS + [
    path('accounts/', include('allauth.urls')),
    path('api/v1/', include('apps.api.urls')),
    path('', include('apps.cuentas.urls')),
    path('.well-known/security.txt', security_txt),
    path('.well-known/oauth-authorization-server', oauth_metadata),
    path('', include('apps.core.urls')),
    path('', include('apps.contenidos.urls')),
    path('', include('apps.buscador.urls')),
    path('', include('apps.qr.urls')),
    path('trivia/', include('apps.trivia.urls')),
    path('panel/', include('apps.estadisticas.urls')),
    path('panel/', include('apps.contenidos.urls_panel')),
    path('panel/', include('apps.buscador.urls_panel')),
    path('panel/', include('apps.qr.urls_panel')),
    path('panel/', include('apps.trivia.urls_panel')),
    path('panel/', include('apps.api.urls_panel')),
]

handler404 = 'apps.core.views.error_404'
handler500 = 'apps.core.views.error_500'
handler403 = 'apps.core.views.error_403'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
