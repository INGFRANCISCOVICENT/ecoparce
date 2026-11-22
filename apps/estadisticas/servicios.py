"""Consultas de estadísticas (RF-11). Las fechas se agrupan en Python con la hora de Colombia,
para no depender de las tablas de zonas horarias de MySQL en PythonAnywhere."""
from collections import Counter
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.buscador.models import Busqueda
from apps.qr.models import CodigoQR, Escaneo, TipoDispositivo
from apps.trivia.models import PartidaTrivia, PreguntaTrivia, RespuestaPartida

DIAS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']


def periodo(dias):
    hoy = timezone.localdate()
    inicio = hoy - timedelta(days=dias - 1)
    desde = timezone.make_aware(datetime.combine(inicio, time.min))
    return inicio, hoy, desde


def por_dia(fechas, inicio, dias):
    conteo = Counter(timezone.localtime(f).date() for f in fechas)
    serie = []
    for i in range(dias):
        d = inicio + timedelta(days=i)
        etiqueta = DIAS[d.weekday()] if dias <= 7 else d.strftime('%d/%m')
        serie.append({'fecha': d, 'etiqueta': etiqueta, 'valor': conteo.get(d, 0)})
    maximo = max([s['valor'] for s in serie] + [1])
    for s in serie:
        s['alto'] = round(130 * s['valor'] / maximo)
    return serie


def resumen(dias=7):
    inicio, hoy, desde = periodo(dias)
    escaneos = Escaneo.objects.filter(fecha_hora__gte=desde)
    busquedas = Busqueda.objects.filter(fecha_hora__gte=desde)
    partidas = PartidaTrivia.objects.filter(iniciada_en__gte=desde)
    terminadas = partidas.filter(finalizada_en__isnull=False)
    total_b = busquedas.count()
    encontradas = busquedas.filter(encontrado=True).count()
    return {
        'dias': dias, 'inicio': inicio, 'fin': hoy,
        'escaneos': escaneos.count(),
        'codigos_activos': CodigoQR.objects.filter(activo=True).count(),
        'busquedas': total_b, 'pct_encontrado': round(100 * encontradas / total_b) if total_b else 0,
        'partidas': terminadas.count(), 'partidas_iniciadas': partidas.count(),
        'puntaje_medio': terminadas.aggregate(m=Avg('puntaje'))['m'],
        'serie_escaneos': por_dia(escaneos.values_list('fecha_hora', flat=True), inicio, dias),
        'sin_resultado': busquedas.filter(encontrado=False).values('termino').annotate(veces=Count('id')).order_by('-veces', 'termino')[:8],
    }


def detalle(dias=30):
    datos = resumen(dias)
    inicio, hoy, desde = periodo(dias)
    escaneos = Escaneo.objects.filter(fecha_hora__gte=desde)
    total = datos['escaneos'] or 1
    datos['por_dispositivo'] = [
        {'nombre': TipoDispositivo(r['tipo_dispositivo']).label, 'valor': r['n'], 'pct': round(100 * r['n'] / total)}
        for r in escaneos.values('tipo_dispositivo').annotate(n=Count('id')).order_by('-n')]
    datos['por_codigo'] = (CodigoQR.objects.filter(escaneos__fecha_hora__gte=desde)
                           .annotate(n=Count('escaneos')).select_related('guia', 'institucion').order_by('-n')[:10])
    datos['top_busquedas'] = (Busqueda.objects.filter(fecha_hora__gte=desde, encontrado=True)
                              .values('termino').annotate(veces=Count('id')).order_by('-veces', 'termino')[:10])
    datos['serie_busquedas'] = por_dia(Busqueda.objects.filter(fecha_hora__gte=desde).values_list('fecha_hora', flat=True), inicio, dias)
    falladas = (RespuestaPartida.objects.filter(respondida_en__gte=desde).values('pregunta')
                .annotate(total=Count('id'), errores=Count('id', filter=Q(es_correcta=False)))
                .order_by('-errores')[:5])
    textos = dict(PreguntaTrivia.objects.filter(pk__in=[f['pregunta'] for f in falladas]).values_list('pk', 'enunciado'))
    datos['preguntas_falladas'] = [{'enunciado': textos.get(f['pregunta'], ''), 'total': f['total'], 'errores': f['errores'],
                                    'pct': round(100 * f['errores'] / f['total']) if f['total'] else 0} for f in falladas if f['errores']]
    return datos
