from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core.permisos import sistema_requerido

from .forms import CodigoQRForm, InstitucionForm
from .models import CodigoQR, Institucion


@sistema_requerido
def lista(request):
    """RF-07: genera un QR automáticamente si no existe ninguno, ofrece creación en 1 clic y muestra siempre la vista previa."""
    if request.method == 'POST' and request.POST.get('rapido'):
        destino = request.POST.get('rapido')
        etiquetas = {'INICIO': 'Acceso principal EcoParce', 'GUIAS': 'Guías de separación',
                     'BUSCADOR': 'Buscador de residuos', 'TRIVIA': 'Trivia ecológica'}
        if destino in etiquetas:
            qr = CodigoQR.objects.create(destino_tipo=destino, ubicacion=etiquetas[destino], creado_por=request.user)
            RegistroAuditoria.registrar(request.user, Accion.CREAR, qr, f'{qr.codigo_corto} → {qr.destino_texto()} ({qr.ubicacion})')
            messages.success(request, f'Código QR {qr.codigo_corto} generado automáticamente para {qr.destino_texto()}.')
            return redirect(f"{request.path}?nuevo={qr.pk}")

    form = CodigoQRForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        qr = form.save(commit=False)
        qr.creado_por = request.user
        qr.save()
        RegistroAuditoria.registrar(request.user, Accion.CREAR, qr, f'{qr.codigo_corto} → {qr.destino_texto()} ({qr.ubicacion})')
        messages.success(request, f'Se creó el código {qr.codigo_corto}. Descárgalo e imprímelo.')
        return redirect(f"{request.path}?nuevo={qr.pk}")

    # Si aún no hay ningún QR, generamos uno principal automáticamente para que esté listo al instante.
    if not CodigoQR.objects.exists():
        qr_auto = CodigoQR.objects.create(destino_tipo='INICIO', ubicacion='Acceso principal EcoParce', creado_por=request.user)
        RegistroAuditoria.registrar(request.user, Accion.CREAR, qr_auto, f'{qr_auto.codigo_corto} → Inicio (generado automáticamente)')

    codigos = CodigoQR.objects.select_related('guia', 'institucion').annotate(lecturas=Count('escaneos'))
    nuevo = None
    if request.GET.get('nuevo', '').isdigit():
        nuevo = codigos.filter(pk=request.GET['nuevo']).first()
    if nuevo is None:
        nuevo = codigos.filter(activo=True).first() or codigos.first()
    return render(request, 'qr/panel/lista.html', {'form': form, 'codigos': codigos, 'nuevo': nuevo})


@sistema_requerido
def imagen(request, pk, formato):
    qr = get_object_or_404(CodigoQR, pk=pk)
    formato = 'svg' if formato == 'svg' else 'png'
    tipo = 'image/svg+xml' if formato == 'svg' else 'image/png'
    respuesta = HttpResponse(qr.generar_imagen(formato), content_type=tipo)
    if request.GET.get('descargar'):
        respuesta['Content-Disposition'] = f'attachment; filename="ecoparce-qr-{qr.codigo_corto}.{formato}"'
    return respuesta


@require_POST
@sistema_requerido
def activar(request, pk):
    """RN-06: un código desactivado no se borra, para no perder sus estadísticas."""
    qr = get_object_or_404(CodigoQR, pk=pk)
    qr.activo = not qr.activo
    qr.save(update_fields=['activo'])
    RegistroAuditoria.registrar(request.user, Accion.ACTIVAR if qr.activo else Accion.DESACTIVAR, qr, qr.codigo_corto)
    messages.success(request, f'Código {qr.codigo_corto} {"activado" if qr.activo else "desactivado"}.')
    return redirect('panel_qr:lista')


@sistema_requerido
def instituciones(request):
    form = InstitucionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        i = form.save()
        RegistroAuditoria.registrar(request.user, Accion.CREAR, i, i.nombre)
        messages.success(request, f'Se registró {i.nombre}.')
        return redirect('panel_qr:instituciones')
    return render(request, 'qr/panel/instituciones.html', {
        'form': form, 'instituciones': Institucion.objects.annotate(codigos=Count('codigos_qr'))})
