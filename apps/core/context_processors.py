from django.conf import settings
from django.utils import timezone


def google_configurado():
    apps = settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APPS', [])
    return bool(apps and apps[0].get('client_id') and apps[0].get('secret'))


def app_version():
    archivo = settings.BASE_DIR / 'VERSION'
    try:
        return archivo.read_text(encoding='utf-8').strip() or '1.3.0'
    except OSError:
        return '1.3.0'


def sitio(request):
    datos = {
        'SITE_URL': settings.SITE_URL,
        'ANIO': timezone.localdate().year,
        'GOOGLE_ACTIVO': google_configurado(),
        'APP_VERSION': app_version(),
    }
    usuario = getattr(request, 'user', None)
    if usuario is not None and usuario.is_authenticated and getattr(usuario, 'es_personal', False) and request.path.startswith('/panel/'):
        from apps.buscador.models import EstadoSugerencia, Sugerencia
        from apps.contenidos.models import EstadoContenido, Guia, Residuo
        en_rev = EstadoContenido.EN_REVISION
        datos['PEND_REVISION'] = (Guia.objects.filter(estado=en_rev).exclude(autor=usuario).count()
                                  + Residuo.objects.filter(estado=en_rev).exclude(autor=usuario).count())
        datos['PEND_SUGERENCIAS'] = Sugerencia.objects.filter(estado=EstadoSugerencia.PENDIENTE).count()
    return datos
