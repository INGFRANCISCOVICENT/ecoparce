import time

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.contenidos.models import Contenedor, EstadoContenido, Residuo
from apps.core.seguridad import limitar
from apps.core.texto import normalizar

from .forms import SugerenciaForm
from .models import Busqueda, EstadoSugerencia, Sugerencia


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


def sugerir(request):
    """RF-13: centro de sugerencias ciudadano (estilo CiudadReporta) y recepción desde el buscador."""
    if request.method == 'GET':
        recientes = Sugerencia.objects.filter(
            estado__in=[EstadoSugerencia.ATENDIDA, EstadoSugerencia.PENDIENTE]
        )[:8]
        mias = request.user.sugerencias.all()[:10] if request.user.is_authenticated else []
        return render(request, 'buscador/sugerencias.html', {
            'form': SugerenciaForm(),
            'recientes': recientes,
            'mias': mias,
            'total_atendidas': Sugerencia.objects.filter(estado=EstadoSugerencia.ATENDIDA).count(),
        })

    desde_pagina = request.POST.get('origen') == 'pagina'
    destino_ok = 'buscador:sugerir' if desde_pagina else 'buscador:buscar'
    form = SugerenciaForm(request.POST)
    ahora = time.time()
    envios = [t for t in request.session.get('sugerencias', []) if ahora - t < 3600]
    # Doble límite: por sesión y por huella temporal de red (no se guarda la IP, RN-08)
    if len(envios) >= settings.SUGERENCIAS_MAX_POR_HORA or not limitar(request, 'sugerencia', settings.SUGERENCIAS_MAX_POR_HORA * 2, 3600):
        messages.error(request, 'Ya recibimos varias sugerencias tuyas. Inténtalo más tarde.')
        return redirect(destino_ok)
    if not form.is_valid():
        if desde_pagina:
            recientes = Sugerencia.objects.filter(
                estado__in=[EstadoSugerencia.ATENDIDA, EstadoSugerencia.PENDIENTE]
            )[:8]
            mias = request.user.sugerencias.all()[:10] if request.user.is_authenticated else []
            return render(request, 'buscador/sugerencias.html', {
                'form': form, 'recientes': recientes, 'mias': mias,
                'total_atendidas': Sugerencia.objects.filter(estado=EstadoSugerencia.ATENDIDA).count(),
            }, status=400)
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
    return redirect(destino_ok)


def escanear(request):
    """RF-16: escanear el código de barras de un producto o un QR de EcoParce."""
    return render(request, 'buscador/escanear.html')


def autocompletar(request):
    """Sugerencias instantáneas al escribir en el buscador (con color de bolsa y rate limit)."""
    from django.http import JsonResponse

    if not limitar(request, 'autocompletar', 90, 60):
        resp = JsonResponse({'items': []}, status=429)
        resp['Cache-Control'] = 'no-store'
        return resp
    q = (request.GET.get('q') or '').strip()[:60]
    if len(q) < 2:
        resp = JsonResponse({'items': []})
        resp['Cache-Control'] = 'no-store'
        return resp
    items = [
        {
            'nombre': r.nombre,
            'bolsa': r.contenedor.nombre,
            'codigo': r.contenedor.codigo,
        }
        for r in buscar_residuos(q)[:6]
    ]
    resp = JsonResponse({'items': items})
    resp['Cache-Control'] = 'no-store'
    return resp


def asistente_consultar(request):
    """API JSON del Asistente Experto EcoBot: consulta la base real de residuos y guías con rate limit."""
    from django.http import JsonResponse

    if not limitar(request, 'asistente', 45, 60):
        resp = JsonResponse({'error': 'Demasiadas consultas seguidas. Espera unos segundos e intenta de nuevo.'}, status=429)
        resp['Cache-Control'] = 'no-store'
        return resp

    q = (request.GET.get('q') or '').strip()[:100]
    if not q:
        resp = JsonResponse({'encontrado': False, 'mensaje': 'Escribe el nombre de un residuo o una duda sobre reciclaje.'})
        resp['Cache-Control'] = 'no-store'
        return resp

    qn = normalizar(q)
    # Respuestas rápidas para preguntas normativas generales
    if any(p in qn for p in ('2184', 'resolucion', 'codigo de colores', 'bolsa blanca', 'bolsa negra', 'bolsa verde')):
        resp = JsonResponse({
            'encontrado': True,
            'residuo': 'Código de colores en Colombia (Res. 2184 de 2019)',
            'contenedor': 'Blanca · Negra · Verde · Posconsumo',
            'codigo': 'VERDE',
            'pasos': [
                'Bolsa Blanca: aprovechables limpios y secos (plástico, vidrio, cartón, papel, metales).',
                'Bolsa Negra: no aprovechables (servilletas, papel higiénico, cartón con grasa).',
                'Bolsa Verde: orgánicos aprovechables (cáscaras, restos de comida cruda, cuncho de café).',
                'Posconsumo: pilas, aceite usado, bombillos, medicamentos vencidos y RAEE.',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Ver todas las guías oficiales',
            'puntos_url': reverse('contenidos:puntos'),
            'relacionados': ['Botella PET', 'Aceite usado', 'Pilas'],
        })
        resp['Cache-Control'] = 'no-store'
        return resp

    resultados = buscar_residuos(q)
    if resultados:
        principal = resultados[0]
        guia_pub = principal.guia if principal.guia and principal.guia.publicado else None
        datos = {
            'encontrado': True,
            'residuo': principal.nombre,
            'contenedor': principal.contenedor.nombre,
            'codigo': principal.contenedor.codigo,
            'es_especial': principal.es_especial,
            'pasos': principal.pasos[:4],
            'guia_url': guia_pub.get_absolute_url() if guia_pub else reverse('contenidos:guias'),
            'guia_titulo': f'Ver guía: {guia_pub.titulo}' if guia_pub else 'Ver guías de separación',
            'puntos_url': f"{reverse('contenidos:puntos')}?residuo={principal.pk}" if principal.es_especial else '',
            'relacionados': [r.nombre for r in resultados[1:4]],
        }
    else:
        datos = {
            'encontrado': False,
            'mensaje': f'No encontré «{q}» exacto en nuestro catálogo todavía. Mientras lo revisamos, no lo mezcles con reciclables limpios.',
            'buscar_url': f"{reverse('buscador:buscar')}?q={q}",
            'sugerir_url': reverse('buscador:sugerir'),
        }
    resp = JsonResponse(datos)
    resp['Cache-Control'] = 'no-store'
    return resp


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


@require_POST
def analizar_foto_vista(request):
    """POST /escanear/foto/ — Analiza una foto del producto/residuo en memoria y devuelve la bolsa correcta."""
    from django.http import JsonResponse

    from .vision import analizar_foto

    if not limitar(request, 'escaneo_foto', 30, 600):
        return JsonResponse({'error': 'Demasiadas fotos seguidas. Espera unos minutos.'}, status=429)

    tipo_manual = (request.POST.get('tipo') or '').strip().lower()
    archivo = request.FILES.get('foto')
    if not archivo and not tipo_manual:
        return JsonResponse({'error': 'Toma o selecciona una foto del producto para analizarla.'}, status=400)

    try:
        datos = analizar_foto(archivo.read() if archivo else b'', tipo_manual=tipo_manual)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    if datos['codigo'] == Contenedor.POSCONSUMO:
        datos['puntos_url'] = reverse('contenidos:puntos')
    Busqueda.objects.create(termino=f"foto {normalizar(datos['material'])}"[:100], encontrado=True)
    resp = JsonResponse({'ok': True, **datos})
    resp['Cache-Control'] = 'no-store'
    return resp
