import difflib
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

# Equivalencias coloquiales y términos frecuentes que complementan los sinónimos del catálogo.
ALIAS_BUSQUEDA = {
    'pc': 'celular', 'computador': 'celular', 'computadora': 'celular', 'portatil': 'celular',
    'laptop': 'celular', 'monitor': 'celular', 'teclado': 'celular', 'mouse': 'celular',
    'cargador': 'celular', 'audifonos': 'celular', 'televisor': 'celular', 'electrodomestico': 'celular',
    'pet': 'botella', 'gaseosa': 'botella', 'tarro': 'botella', 'galon': 'botella',
    'foco': 'bombillo', 'lampara': 'bombillo', 'tubo': 'bombillo',
    'pastillas': 'medicamento', 'jarabe': 'medicamento', 'remedio': 'medicamento',
    'mecato': 'papas', 'chitos': 'papas', 'doritos': 'papas', 'golosina': 'papas',
    'panal': 'higienico', 'toalla': 'higienico', 'copito': 'higienico',
    'banano': 'cascara', 'manzana': 'cascara', 'naranja': 'cascara', 'fruta': 'cascara', 'verdura': 'cascara',
    'pitillo': 'plastico', 'tenedor': 'plastico', 'cuchara': 'plastico',
}
_STOPWORDS = {'de', 'la', 'el', 'los', 'las', 'un', 'una', 'en', 'con', 'sin', 'por', 'para', 'del', 'y', 'o'}


def _similitud_residuo(objetivo, tokens_q, residuo):
    """Calcula la mejor similitud aproximada (0..1) tolerando errores ortográficos."""
    frases = [normalizar(residuo.nombre)] + [normalizar(s) for s in (residuo.sinonimos or '').split(',') if s.strip()]
    mejor = 0.0
    for frase in frases:
        if not frase:
            continue
        r_completa = difflib.SequenceMatcher(None, objetivo, frase).ratio()
        if r_completa > mejor:
            mejor = r_completa
        palabras_f = [p for p in frase.split() if len(p) >= 3 and p not in _STOPWORDS]
        for tq in tokens_q:
            for pf in palabras_f:
                if abs(len(tq) - len(pf)) > 3:
                    continue
                score = difflib.SequenceMatcher(None, tq, pf).ratio()
                if score > mejor:
                    mejor = score
    return mejor


def buscar_residuos(termino):
    """RF-03: busca por nombre, sinónimo, alias coloquial o coincidencia aproximada (tolera errores de escritura)."""
    objetivo = normalizar(termino)
    if not objetivo:
        return []
    publicados = list(Residuo.objects.filter(estado=EstadoContenido.PUBLICADO).select_related('contenedor', 'guia'))
    encontrados = [r for r in publicados if r.coincide_con(termino)]
    if encontrados:
        return sorted(encontrados, key=lambda r: (r.puntuacion(termino), len(r.nombre)))

    # 2. Alias coloquiales (ej. computador -> raee/celular, mecato -> empaque metalizado)
    tokens = [t for t in objetivo.split() if len(t) >= 2 and t not in _STOPWORDS]
    for tok in tokens:
        alias = ALIAS_BUSQUEDA.get(tok)
        if alias:
            por_alias = [r for r in publicados if r.coincide_con(alias)]
            if por_alias:
                return sorted(por_alias, key=lambda r: (r.puntuacion(alias), len(r.nombre)))

    # 3. Búsqueda aproximada tolerante a errores ortográficos (ej. "boteya", "aseite", "ikopor", "vombillo")
    tokens_largos = [t for t in tokens if len(t) >= 3]
    if not tokens_largos and len(objetivo) < 3:
        return []
    candidatos = []
    for r in publicados:
        sim = _similitud_residuo(objetivo, tokens_largos or [objetivo], r)
        if sim >= 0.70:
            candidatos.append((sim, r))
    candidatos.sort(key=lambda par: (-par[0], len(par[1].nombre)))
    return [r for _, r in candidatos[:6]]


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
    """API JSON del Asistente Experto EcoBot: intenciones conversacionales + catálogo oficial con rate limit."""
    from django.http import JsonResponse

    from .asistente import responder_consulta

    if not limitar(request, 'asistente', 45, 60):
        resp = JsonResponse({'error': 'Demasiadas consultas seguidas. Espera unos segundos e intenta de nuevo.'}, status=429)
        resp['Cache-Control'] = 'no-store'
        return resp

    q = (request.GET.get('q') or '').strip()[:100]
    if not q:
        resp = JsonResponse({'encontrado': False, 'mensaje': 'Escribe el nombre de un residuo o una duda sobre reciclaje.'})
        resp['Cache-Control'] = 'no-store'
        return resp

    datos = responder_consulta(q, buscar_residuos)
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

    if datos.get('codigo') == Contenedor.POSCONSUMO:
        datos['puntos_url'] = reverse('contenidos:puntos')
    if datos.get('identificado'):
        Busqueda.objects.create(termino=f"foto {normalizar(datos['material'])}"[:100], encontrado=True)
    resp = JsonResponse({'ok': True, **datos})
    resp['Cache-Control'] = 'no-store'
    return resp
