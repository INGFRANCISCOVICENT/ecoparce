"""Panel de Calidad de Software (ISO/IEC 25010), Seguridad, RLS y gestión de API Keys."""
from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core.cifrado import esta_cifrado
from apps.core.context_processors import google_configurado
from apps.core.permisos import sistema_requerido
from apps.core.rls import POLITICAS_RLS_POSTGRES

from .models import ApiKey, PermisoApi, RegistroGateway


@sistema_requerido
def tablero_calidad(request):
    """GET /panel/calidad/ — Telemetría de seguridad, cifrado, RLS, API Gateway y API Keys."""
    with connection.cursor() as cur:
        cur.execute('SELECT nombre, correo_hash FROM usuario')
        filas_u = cur.fetchall()
    total_usuarios = len(filas_u)
    usuarios_cifrados = sum(1 for nombre, _ in filas_u if not nombre or esta_cifrado(nombre))
    usuarios_hash = sum(1 for _, h in filas_u if h and len(h) == 64)
    pct_cifrado = round((usuarios_cifrados / total_usuarios) * 100) if total_usuarios else 100

    total_gw = RegistroGateway.objects.count()
    bloqueados_gw = RegistroGateway.objects.filter(bloqueado=True).count()
    latencia_media = RegistroGateway.objects.aggregate(avg=Avg('duracion_ms'))['avg'] or 0
    amenazas = list(
        RegistroGateway.objects.filter(bloqueado=True)
        .exclude(motivo_bloqueo='')
        .values('motivo_bloqueo')
        .annotate(total=Count('id'))
        .order_by('-total')[:8]
    )

    clave_recien_creada = request.session.pop('api_key_nueva', None)

    return render(request, 'api/panel/calidad.html', {
        'motor_bd': connection.vendor,
        'total_usuarios': total_usuarios,
        'usuarios_cifrados': usuarios_cifrados,
        'usuarios_hash': usuarios_hash,
        'pct_cifrado': pct_cifrado,
        'politicas_rls': POLITICAS_RLS_POSTGRES,
        'rls_nativo': connection.vendor == 'postgresql',
        'google_ok': google_configurado(),
        'smtp_ok': bool(getattr(settings, 'EMAIL_HOST', '')),
        'codigo_registro': bool(getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED', False)),
        'total_gw': total_gw,
        'bloqueados_gw': bloqueados_gw,
        'latencia_media': round(latencia_media, 1),
        'amenazas': amenazas,
        'api_keys': ApiKey.objects.select_related('propietario').all()[:20],
        'logs_gw': RegistroGateway.objects.select_related('api_key', 'usuario').all()[:25],
        'clave_recien_creada': clave_recien_creada,
        'permisos_choices': PermisoApi.choices,
    })


@sistema_requerido
@require_POST
def crear_llave_panel(request):
    """POST /panel/calidad/llaves/crear/ — Genera una API Key desde el panel (solo SISTEMA)."""
    nombre = (request.POST.get('nombre') or '').strip()[:120]
    permisos = request.POST.get('permisos') or PermisoApi.LECTURA_ESCRITURA
    if permisos not in (PermisoApi.LECTURA, PermisoApi.LECTURA_ESCRITURA):
        permisos = PermisoApi.LECTURA
    try:
        limite = min(max(int(request.POST.get('limite', '60')), 5), 600)
    except ValueError:
        limite = 60

    if len(nombre) < 2:
        messages.error(request, 'Escribe un nombre descriptivo para la API Key (mínimo 2 caracteres).')
        return redirect('panel_api:calidad')

    llave, clave_plana = ApiKey.generar(
        nombre=nombre, propietario=request.user, permisos=permisos, limite_por_minuto=limite,
    )
    RegistroAuditoria.registrar(request.user, Accion.CREAR, llave, f'API Key {llave.nombre} ({llave.permisos})')
    request.session['api_key_nueva'] = {'nombre': llave.nombre, 'clave': clave_plana}
    messages.success(request, f'API Key «{llave.nombre}» generada. Cópiala ahora: no se volverá a mostrar.')
    return redirect('panel_api:calidad')


@sistema_requerido
@require_POST
def alternar_llave_panel(request, pk):
    """POST /panel/calidad/llaves/<pk>/alternar/ — Activa o revoca una API Key."""
    llave = get_object_or_404(ApiKey, pk=pk)
    llave.activa = not llave.activa
    llave.save(update_fields=['activa'])
    accion = Accion.ACTIVAR if llave.activa else Accion.DESACTIVAR
    RegistroAuditoria.registrar(request.user, accion, llave, f'API Key {llave.nombre}')
    estado = 'activada' if llave.activa else 'revocada'
    messages.success(request, f'API Key «{llave.nombre}» {estado}.')
    return redirect('panel_api:calidad')
