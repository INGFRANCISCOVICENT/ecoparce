from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render

from apps.core.seguridad import limitar

from .models import CodigoQR, TipoDestino, tipo_dispositivo


def redirigir(request, codigo):
    """RF-01 / RN-06: un QR activo registra la lectura anónima y redirige; uno inactivo muestra un aviso."""
    qr = CodigoQR.objects.select_related('guia').filter(codigo_corto=codigo.upper()[:8]).first()
    if qr is None or not qr.activo:
        return render(request, 'qr/no_disponible.html', status=404)
    # Relecturas del mismo QR por la misma persona en 10 minutos no se cuentan dos veces
    if limitar(request, f'escaneo:{qr.pk}', 1, settings.ESCANEO_VENTANA_SEGUNDOS):
        qr.registrar_escaneo(tipo_dispositivo(request.META.get('HTTP_USER_AGENT')))
    destino = qr.destino_url()
    if qr.destino_tipo == TipoDestino.GUIA and qr.guia and qr.guia.publicado:
        destino += f'?qr={qr.codigo_corto}'
    if qr.destino_tipo == TipoDestino.TRIVIA:
        request.session['qr_origen'] = qr.pk
    respuesta = HttpResponseRedirect(destino)
    respuesta['Cache-Control'] = 'no-store'  # para que cada lectura llegue al servidor y se cuente
    return respuesta
