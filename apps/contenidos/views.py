from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page

from apps.qr.models import CodigoQR

from .models import Contenedor, EstadoContenido, FuentePunto, Guia, PuntoEntrega, Residuo, TipoGuia


def guias(request):
    publicadas = Guia.publicadas.select_related('contenedor')
    return render(request, 'contenidos/guias.html', {
        'secciones': [(t.label, [g for g in publicadas if g.tipo == t.value]) for t in TipoGuia],
    })


def guia(request, slug):
    """RN-01: solo se muestran guías publicadas; las demás responden 404."""
    g = get_object_or_404(Guia.publicadas.select_related('contenedor'), slug=slug)
    origen = None
    codigo = request.GET.get('qr', '')[:8]
    if codigo:
        origen = CodigoQR.objects.filter(codigo_corto=codigo, activo=True).select_related('institucion').first()
    residuos = g.residuos.filter(estado=EstadoContenido.PUBLICADO).select_related('contenedor')
    return render(request, 'contenidos/guia.html', {
        'guia': g, 'origen': origen, 'residuos': residuos,
        'url_compartir': request.build_absolute_uri(g.get_absolute_url()),
    })


def manejo(request):
    """RF-04: residuos especiales; cada uno lleva al mapa de puntos oficiales que lo reciben."""
    especiales = Residuo.objects.filter(estado=EstadoContenido.PUBLICADO, es_especial=True).order_by('nombre')
    elegido = None
    rid = request.GET.get('residuo')
    if rid and rid.isdigit():
        elegido = especiales.filter(pk=rid).first()
    return render(request, 'contenidos/manejo.html', {
        'especiales': especiales, 'elegido': elegido,
        'guias_manejo': Guia.publicadas.filter(tipo__in=[TipoGuia.MANEJO, TipoGuia.ESPECIAL]),
    })


def _puntos_filtrados(request):
    puntos = PuntoEntrega.objects.filter(activo=True, latitud__isnull=False)
    rid = request.GET.get('residuo', '')
    residuo = None
    if rid.isdigit():
        residuo = Residuo.objects.filter(pk=rid, es_especial=True, estado=EstadoContenido.PUBLICADO).first()
        if residuo:
            puntos = puntos.filter(residuos=residuo)
    localidad = request.GET.get('localidad', '')
    if localidad:
        puntos = puntos.filter(localidad=localidad)
    return puntos.distinct(), residuo, localidad


def puntos(request):
    """RF-12: mapa de puntos de recolección oficiales. La ubicación del visitante se usa solo en su navegador."""
    lista, residuo, localidad = _puntos_filtrados(request)
    especiales = Residuo.objects.filter(estado=EstadoContenido.PUBLICADO, es_especial=True, puntos__activo=True).distinct().order_by('nombre')
    return render(request, 'contenidos/puntos.html', {
        'residuo': residuo, 'localidad': localidad, 'especiales': especiales,
        'localidades': PuntoEntrega.objects.filter(activo=True).order_by('localidad').values_list('localidad', flat=True).distinct(),
        'total': lista.count(), 'primeros': lista.order_by('localidad', 'nombre')[:20],
        'hay_oficiales': PuntoEntrega.objects.filter(fuente=FuentePunto.SDA, activo=True).exists(),
        'actualizado': PuntoEntrega.objects.filter(fuente=FuentePunto.SDA).order_by('-actualizado_en').values_list('actualizado_en', flat=True).first(),
    })


@cache_page(60 * 30)
def puntos_datos(request):
    """Datos compactos para el mapa (sin datos personales)."""
    lista, _, _ = _puntos_filtrados(request)
    datos = [{'n': p.nombre, 'd': p.direccion, 'l': p.localidad, 'b': p.barrio, 'h': p.horario, 't': p.telefono,
              'la': float(p.latitud), 'lo': float(p.longitud), 'r': p.recibe or ', '.join(r.nombre for r in p.residuos.all()),
              'f': p.verificado_en.isoformat() if p.verificado_en else '', 'o': p.fuente}
             for p in lista.prefetch_related('residuos')[:3000]]
    return JsonResponse({'puntos': datos})
