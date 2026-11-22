import time

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.contenidos.models import EstadoContenido, Residuo
from apps.core.seguridad import limitar
from apps.core.texto import normalizar

from .forms import SugerenciaForm
from .models import Busqueda, Sugerencia


def buscar_residuos(termino):
    """RF-03: busca por nombre o sinónimo, sin importar mayúsculas ni tildes. Devuelve la lista ordenada."""
    if not normalizar(termino):
        return []
    publicados = Residuo.objects.filter(estado=EstadoContenido.PUBLICADO).select_related('contenedor', 'guia')
    encontrados = [r for r in publicados if r.coincide_con(termino)]
    return sorted(encontrados, key=lambda r: (r.puntuacion(termino), len(r.nombre)))


def buscar(request):
    q = request.GET.get('q', '').strip()[:100]
    resultados = buscar_residuos(q) if q else []
    if q and limitar(request, 'busqueda', 120, 3600):
        # RF-10 / RN-08: registro anónimo del término normalizado (con tope para que no se inflen las estadísticas)
        Busqueda.objects.create(termino=normalizar(q)[:100] or q, encontrado=bool(resultados),
                                residuo=resultados[0] if resultados else None)
    principal = resultados[0] if resultados else None
    guia_publicada = principal.guia if principal and principal.guia and principal.guia.publicado else None
    return render(request, 'buscador/buscar.html', {
        'q': q, 'principal': principal, 'otros': resultados[1:6], 'total': len(resultados),
        'guia': guia_publicada, 'form': SugerenciaForm(initial={'termino': q}),
    })


@require_POST
def sugerir(request):
    """RF-13: el visitante propone un residuo que no encontró. Límite por sesión y campo trampa contra robots."""
    form = SugerenciaForm(request.POST)
    ahora = time.time()
    envios = [t for t in request.session.get('sugerencias', []) if ahora - t < 3600]
    # Doble límite: por sesión y por huella temporal de red (no se guarda la IP, RN-08)
    if len(envios) >= settings.SUGERENCIAS_MAX_POR_HORA or not limitar(request, 'sugerencia', settings.SUGERENCIAS_MAX_POR_HORA * 2, 3600):
        messages.error(request, 'Ya recibimos varias sugerencias tuyas. Inténtalo más tarde.')
        return redirect('buscador:buscar')
    if not form.is_valid():
        termino = request.POST.get('termino', '')
        resultados = buscar_residuos(termino)
        return render(request, 'buscador/buscar.html', {'q': termino, 'principal': None, 'otros': resultados[:5],
                                                         'total': 0, 'form': form}, status=400)
    if not form.cleaned_data.get('sitio_web'):
        Sugerencia.objects.create(termino=form.cleaned_data['termino'], comentario=form.cleaned_data['comentario'],
                                  usuario=request.user if request.user.is_authenticated else None)
    envios.append(ahora)
    request.session['sugerencias'] = envios
    messages.success(request, '¡Gracias, parce! Revisaremos tu sugerencia y la agregaremos pronto.')
    return redirect('buscador:buscar')


def escanear(request):
    """RF-16: escanear el código de barras de un producto o un QR de EcoParce."""
    return render(request, 'buscador/escanear.html')


def producto(request, codigo):
    """Consulta el empaque de un producto y responde a qué bolsa va cada parte (JSON)."""
    from django.http import JsonResponse

    from .escaner import CODIGO_VALIDO, analizar, buscar_producto
    if not CODIGO_VALIDO.match(codigo):
        return JsonResponse({'error': 'Código no válido. Debe tener entre 8 y 14 dígitos.'}, status=400)
    if not limitar(request, 'escaneo_producto', 60, 600):
        return JsonResponse({'error': 'Demasiadas consultas seguidas. Espera unos minutos.'}, status=429)
    fuente, datos = buscar_producto(codigo)
    if not datos:
        Busqueda.objects.create(termino=f'codigo {codigo}'[:100], encontrado=False)
        return JsonResponse({'encontrado': False, 'codigo': codigo})
    nombre = (datos.get('product_name_es') or datos.get('product_name') or '').strip()[:120]
    partes = analizar(datos)
    for p in partes:
        if p.get('residuo'):
            r = Residuo.objects.filter(nombre=p['residuo'], estado=EstadoContenido.PUBLICADO).first()
            if r:
                p['puntos_url'] = f"{reverse('contenidos:puntos')}?residuo={r.pk}"
    Busqueda.objects.create(termino=normalizar(nombre or f'codigo {codigo}')[:100], encontrado=bool(partes))
    return JsonResponse({'encontrado': True, 'codigo': codigo, 'nombre': nombre or 'Producto sin nombre',
                         'marca': (datos.get('brands') or '').split(',')[0].strip()[:80], 'partes': partes,
                         'fuente': fuente, 'fuente_url': f'https://world.openfoodfacts.org/product/{codigo}'})
