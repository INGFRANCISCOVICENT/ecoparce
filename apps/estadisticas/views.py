import csv

from django.http import HttpResponse
from django.shortcuts import render

from apps.contenidos.models import EstadoContenido, Guia, Residuo
from apps.core.permisos import panel_requerido, sistema_requerido

from . import servicios


@panel_requerido
def resumen(request):
    datos = servicios.resumen(7)
    en_rev = EstadoContenido.EN_REVISION
    datos['pend_guias'] = Guia.objects.filter(estado=en_rev).count()
    datos['pend_residuos'] = Residuo.objects.filter(estado=en_rev).count()
    datos['publicadas'] = Guia.publicadas.count()
    datos['residuos_publicados'] = Residuo.objects.filter(estado=EstadoContenido.PUBLICADO).count()
    return render(request, 'estadisticas/resumen.html', datos)


def _dias(request):
    try:
        d = int(request.GET.get('dias', 30))
    except ValueError:
        d = 30
    return d if d in (7, 30, 90) else 30


@sistema_requerido
def detalle(request):
    return render(request, 'estadisticas/detalle.html', {**servicios.detalle(_dias(request)), 'periodos': [7, 30, 90]})


def _celda_csv_segura(valor):
    """Protección OWASP contra inyección de fórmulas en Excel/Calc (=, +, -, @)."""
    texto = str(valor) if valor is not None else ''
    if texto and texto[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + texto
    return texto


@sistema_requerido
def exportar(request):
    """Exporta la serie diaria del periodo a CSV (se abre en Excel, protegido contra CSV Injection)."""
    datos = servicios.detalle(_dias(request))
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="ecoparce-estadisticas-{datos["inicio"]}-{datos["fin"]}.csv"'
    respuesta['Cache-Control'] = 'no-store'
    respuesta.write('\ufeff')
    w = csv.writer(respuesta, delimiter=';')
    w.writerow(['Fecha', 'Lecturas de QR', 'Búsquedas'])
    for e, b in zip(datos['serie_escaneos'], datos['serie_busquedas']):
        w.writerow([e['fecha'].isoformat(), e['valor'], b['valor']])
    w.writerow([])
    w.writerow(['Búsquedas sin resultado', 'Veces'])
    for r in datos['sin_resultado']:
        w.writerow([_celda_csv_segura(r['termino']), r['veces']])
    return respuesta
