import json
import time

from allauth.account.authentication import get_authentication_records
from allauth.account.decorators import reauthentication_required
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core.permisos import sistema_requerido
from apps.core.seguridad import evento

from .forms import AdministradorForm, AutorizacionForm, EliminarCuentaForm, UsuarioEditarForm
from .models import Consentimiento, EstadoSolicitudAdmin, Rol, SolicitudAdmin, Usuario
from .sesiones import cerrar_sesiones

FRESCURA_SEGUNDOS = 15 * 60


def ingresar(request):
    """Compatibilidad con la ruta del diseño: /panel/ingresar/ lleva al inicio de sesión con Google."""
    return redirect(f"{reverse('account_login')}?next=/panel/")


def _destino_seguro(request, defecto='/'):
    destino = request.POST.get('next') or request.GET.get('next') or defecto
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        if destino.startswith('/panel/') and not getattr(request.user, 'es_personal', False):
            return reverse('cuentas:mi_cuenta')
        return destino
    return defecto


def _ingreso_reciente(request):
    """¿La persona se autenticó (Google, contraseña o MFA) hace menos de 15 minutos?"""
    ahora = time.time()
    return any(ahora - r.get('at', 0) < FRESCURA_SEGUNDOS for r in get_authentication_records(request, request.user))


# --------------------------------------------------------------------------- visitante
@login_required
def autorizacion(request):
    """Autorización previa, expresa e informada para tratar datos personales (Ley 1581 de 2012, art. 9)."""
    version = settings.VERSION_AVISO_PRIVACIDAD
    form = AutorizacionForm(request.POST or None)
    if request.method == 'POST':
        if request.POST.get('decision') == 'rechazo':
            usuario = request.user
            logout(request)
            if usuario.rol == Rol.VISITANTE and not usuario.consentimientos.exists():
                usuario.delete()  # no se conserva ningún dato de quien no autorizó
                evento('cuenta_rechazo_autorizacion', request)
            messages.info(request, 'No guardamos tus datos. Puedes seguir usando EcoParce sin cuenta.')
            return redirect('core:inicio')
        if form.is_valid():
            Consentimiento.objects.update_or_create(
                usuario=request.user,
                version=version,
                defaults={
                    'acepta_terminos': True,
                    'mayor_edad_o_acudiente': True,
                    'acepta_marketing': bool(form.cleaned_data.get('acepta_marketing')),
                },
            )
            request.session['consentimiento'] = version
            evento('consentimiento_aceptado', request, version=version)
            return redirect(_destino_seguro(request, reverse('cuentas:mi_cuenta')))
    return render(request, 'cuentas/autorizacion.html', {'form': form, 'version': version,
                                                          'next': _destino_seguro(request, '')})


@login_required
def comunicaciones(request):
    """Preferencias y baja en un clic de comunicaciones educativas/novedades (marketing opcional)."""
    consentimiento = request.user.consentimientos.order_by('-aceptado_en').first()
    if request.method == 'POST':
        accion = request.POST.get('accion', 'baja')
        aceptar = accion == 'alta'
        if consentimiento:
            consentimiento.acepta_marketing = aceptar
            consentimiento.save(update_fields=['acepta_marketing', 'actualizado_en'])
        else:
            consentimiento = Consentimiento.objects.create(
                usuario=request.user, version=settings.VERSION_AVISO_PRIVACIDAD, acepta_marketing=aceptar,
            )
        evento('marketing_actualizado', request, acepta_marketing=aceptar)
        if aceptar:
            messages.success(request, 'Activaste las novedades educativas por correo. Puedes darte de baja cuando quieras.')
        else:
            messages.success(request, 'Te dimos de baja de los correos de novedades. Solo recibirás mensajes de seguridad si los solicitas.')
        destino = request.POST.get('next')
        if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(destino)
        return redirect('cuentas:comunicaciones')
    return render(request, 'cuentas/comunicaciones.html', {'consentimiento': consentimiento})


@login_required
def mi_cuenta(request):
    from apps.trivia.models import obtener_insignias, progreso_niveles
    u = request.user
    partidas = u.partidas.filter(finalizada_en__isnull=False).order_by('-iniciada_en')
    resumen = None
    if partidas:
        puntajes = [p.puntaje for p in partidas]
        resumen = {'jugadas': len(puntajes), 'mejor': max(puntajes),
                   'promedio': sum(puntajes) / len(puntajes), 'perfectas': sum(1 for p in partidas if p.puntaje == p.total_preguntas)}
    social = u.socialaccount_set.filter(provider='google').first()
    insignias = obtener_insignias(usuario=u)
    return render(request, 'cuentas/mi_cuenta.html', {
        'partidas': partidas[:10], 'resumen': resumen, 'sugerencias': u.sugerencias.all()[:10],
        'google': social, 'consentimiento': u.consentimientos.order_by('-aceptado_en').first(),
        'tiene_mfa': u.tiene_mfa(), 'eliminar_form': EliminarCuentaForm(),
        'insignias': insignias,
        'insignias_obtenidas': sum(1 for i in insignias if i['obtenida']),
        'progreso_trivia': progreso_niveles(usuario=u),
        'solicitud_pendiente': u.solicitudes_admin.filter(estado=EstadoSolicitudAdmin.PENDIENTE).first(),
    })


@require_POST
@login_required
def solicitar_admin(request):
    """Permite a un visitante registrado solicitar aprobación para ser administrador."""
    u = request.user
    if u.es_personal:
        messages.info(request, 'Tu cuenta ya tiene permisos de administrador.')
        return redirect('cuentas:mi_cuenta')
    if u.solicitudes_admin.filter(estado=EstadoSolicitudAdmin.PENDIENTE).exists():
        messages.info(request, 'Ya tienes una solicitud pendiente de revisión por el administrador del sistema.')
        return redirect('cuentas:mi_cuenta')
    motivo = (request.POST.get('motivo') or '').strip()[:300]
    if len(motivo) < 8:
        messages.error(request, 'Cuéntanos brevemente por qué deseas ser administrador (mínimo 8 caracteres).')
        return redirect('cuentas:mi_cuenta')
    SolicitudAdmin.objects.create(usuario=u, motivo=motivo)
    evento('solicitud_admin_creada', request, usuario=u)
    messages.success(request, 'Enviamos tu solicitud. El administrador del sistema (fjnv1305@gmail.com) la revisará en el panel.')
    return redirect('cuentas:mi_cuenta')


@login_required
def exportar_datos(request):
    """Derecho de acceso (Ley 1581, art. 8): descarga de todos los datos personales en JSON."""
    u = request.user
    datos = {
        'generado_en': timezone.now().isoformat(),
        'cuenta': {'nombre': u.nombre, 'correo': u.correo, 'rol': u.get_rol_display(),
                   'creada_en': u.creado_en.isoformat(), 'ultimo_acceso': u.last_login.isoformat() if u.last_login else None},
        'google': [{'proveedor': s.provider, 'identificador': s.uid} for s in u.socialaccount_set.all()],
        'autorizaciones': [{
            'version': c.version,
            'acepta_terminos': c.acepta_terminos,
            'mayor_edad_o_acudiente': c.mayor_edad_o_acudiente,
            'acepta_marketing': c.acepta_marketing,
            'aceptada_en': c.aceptado_en.isoformat(),
        } for c in u.consentimientos.all()],
        'partidas_trivia': [{'fecha': p.iniciada_en.isoformat(), 'nivel': p.nivel, 'puntaje': p.puntaje, 'total': p.total_preguntas}
                            for p in u.partidas.all()],
        'insignias_trivia': [{'codigo': i.codigo, 'nombre': i.get_codigo_display(), 'obtenida_en': i.obtenida_en.isoformat()}
                             for i in u.insignias.all()],
        'sugerencias': [{'fecha': s.fecha_hora.isoformat(), 'residuo': s.termino, 'comentario': s.comentario,
                         'estado': s.get_estado_display()} for s in u.sugerencias.all()],
        'verificacion_dos_pasos': u.tiene_mfa(),
    }
    evento('datos_exportados', request)
    r = HttpResponse(json.dumps(datos, ensure_ascii=False, indent=2), content_type='application/json; charset=utf-8')
    r['Content-Disposition'] = 'attachment; filename="mis-datos-ecoparce.json"'
    return r


@require_POST
@login_required
def eliminar_cuenta(request):
    """Derecho de supresión: borra la cuenta; las partidas y sugerencias quedan anónimas."""
    u = request.user
    if u.es_personal:
        messages.error(request, 'Una cuenta de administrador la desactiva el administrador del sistema.')
        return redirect('cuentas:mi_cuenta')
    form = EliminarCuentaForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Escribe ELIMINAR para confirmar.')
        return redirect('cuentas:mi_cuenta')
    if not _ingreso_reciente(request):
        logout(request)
        messages.warning(request, 'Por seguridad, vuelve a ingresar con Google y repite la eliminación.')
        return redirect(f"{reverse('account_login')}?next={reverse('cuentas:mi_cuenta')}")
    with transaction.atomic():
        pk = u.pk
        logout(request)
        Usuario.objects.filter(pk=pk).delete()
    evento('cuenta_eliminada', request, usuario_id=pk)
    messages.success(request, 'Eliminamos tu cuenta y tus datos personales. ¡Gracias por reciclar con EcoParce!')
    return redirect('core:inicio')


# --------------------------------------------------------------------------- panel: administradores
@sistema_requerido
def usuarios(request):
    return render(request, 'cuentas/usuarios.html', {
        'usuarios': Usuario.objects.filter(rol__in=[Rol.CONTENIDO, Rol.SISTEMA]).prefetch_related('socialaccount_set'),
        'con_mfa': set(Authenticator.objects.filter(type=Authenticator.Type.TOTP).values_list('user_id', flat=True)),
        'visitantes': Usuario.objects.filter(rol=Rol.VISITANTE).count(),
        'solicitudes': SolicitudAdmin.objects.filter(estado=EstadoSolicitudAdmin.PENDIENTE).select_related('usuario'),
    })


@require_POST
@sistema_requerido
def resolver_solicitud(request, pk):
    """Aprueba (como Admin de contenido o del sistema) o rechaza una solicitud de administrador."""
    sol = get_object_or_404(SolicitudAdmin.objects.select_related('usuario'), pk=pk, estado=EstadoSolicitudAdmin.PENDIENTE)
    accion = request.POST.get('accion', '')
    u = sol.usuario
    if accion in ('aprobar_contenido', 'aprobar_sistema'):
        nuevo_rol = Rol.SISTEMA if accion == 'aprobar_sistema' else Rol.CONTENIDO
        u.rol = nuevo_rol
        u.is_active = True
        u.save(update_fields=['rol', 'is_active'])
        sol.estado = EstadoSolicitudAdmin.APROBADA
        sol.resuelta_por = request.user
        sol.resuelta_en = timezone.now()
        sol.save(update_fields=['estado', 'resuelta_por', 'resuelta_en'])
        cerrar_sesiones(u)
        RegistroAuditoria.registrar(request.user, Accion.EDITAR, u, f'Aprobó solicitud de {u.correo} como {u.get_rol_display()}')
        messages.success(request, f'Aprobaste a {u.nombre} ({u.correo}) como {u.get_rol_display()}.')
    elif accion == 'rechazar':
        sol.estado = EstadoSolicitudAdmin.RECHAZADA
        sol.resuelta_por = request.user
        sol.resuelta_en = timezone.now()
        sol.save(update_fields=['estado', 'resuelta_por', 'resuelta_en'])
        RegistroAuditoria.registrar(request.user, Accion.EDITAR, u, f'Rechazó solicitud de administrador de {u.correo}')
        messages.info(request, f'Rechazaste la solicitud de {u.nombre}.')
    return redirect('cuentas:usuarios')


@sistema_requerido
@reauthentication_required
def usuario_crear(request):
    """RF-15: autoriza un correo como administrador. Exige haber confirmado la identidad hace menos de 5 minutos."""
    form = AdministradorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        u = form.existente
        if u:  # un visitante que ya tenía cuenta pasa a ser administrador
            u.rol, u.nombre = d['rol'], d['nombre']
            u.save(update_fields=['rol', 'nombre'])
            cerrar_sesiones(u)
        else:
            u = Usuario.objects.create_user(d['correo'], d['nombre'], rol=d['rol'])
        RegistroAuditoria.registrar(request.user, Accion.CREAR, u, f'Autorizó a {u.correo} como {u.get_rol_display()}')
        messages.success(request, f'{u.nombre} ya puede entrar al panel con su cuenta de Google {u.correo}. '
                                  'La primera vez deberá activar la verificación en dos pasos.')
        return redirect('cuentas:usuarios')
    return render(request, 'cuentas/usuario_form.html', {'form': form, 'titulo': 'Nuevo administrador'})


@sistema_requerido
@reauthentication_required
def usuario_editar(request, pk):
    u = get_object_or_404(Usuario, pk=pk)
    form = UsuarioEditarForm(request.POST or None, instance=u, editor=request.user)
    if request.method == 'POST' and 'restablecer_mfa' in request.POST:
        if u == request.user:
            raise PermissionDenied
        n = Authenticator.objects.filter(user=u).delete()[0]
        cerrar_sesiones(u)
        RegistroAuditoria.registrar(request.user, Accion.EDITAR, u, f'Restableció la verificación en dos pasos de {u.correo}')
        evento('mfa_restablecida_por_admin', request, afectado=u.correo, autenticadores=n)
        messages.success(request, f'Se restableció la verificación en dos pasos de {u.nombre}. Deberá configurarla al volver a entrar.')
        return redirect('cuentas:usuarios')
    if request.method == 'POST' and form.is_valid():
        cambios = ', '.join(form.changed_data) or 'sin cambios'
        form.save()
        accion = Accion.EDITAR
        if 'is_active' in form.changed_data:
            accion = Accion.ACTIVAR if u.is_active else Accion.DESACTIVAR
        if {'is_active', 'rol'} & set(form.changed_data):
            cerrar_sesiones(u)  # los permisos nuevos rigen de inmediato
        RegistroAuditoria.registrar(request.user, accion, u, f'{u.correo}: {cambios}')
        messages.success(request, f'Se actualizó la cuenta de {u.nombre}.')
        return redirect('cuentas:usuarios')
    return render(request, 'cuentas/usuario_form.html', {
        'form': form, 'objeto': u, 'titulo': f'Editar · {u.nombre}', 'tiene_mfa': u.tiene_mfa(),
        'google': u.socialaccount_set.filter(provider='google').first()})


@sistema_requerido
def auditoria(request):
    registros = RegistroAuditoria.objects.select_related('usuario')
    accion = request.GET.get('accion', '')
    if accion in Accion.values:
        registros = registros.filter(accion=accion)
    pagina = Paginator(registros, 40).get_page(request.GET.get('p'))
    return render(request, 'cuentas/auditoria.html', {'pagina': pagina, 'acciones': Accion.choices, 'accion': accion})
