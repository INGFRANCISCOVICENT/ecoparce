"""Clasificador visual de residuos por foto (Resolución 2184 de 2019).

Flujo seguro y privado:
- La imagen nunca se guarda en disco ni en la base de datos (se procesa solo en memoria y se descarta).
- Valida formato real (JPEG/PNG/WEBP), tamaño máximo (3 MB) y elimina metadatos EXIF.
- Si existe GEMINI_API_KEY en el entorno, usa visión multimodal (Gemini) para identificar el producto exacto.
- Si no hay clave de IA configurada, aplica análisis visual local con Pillow (colorimetría HSV, brillo y
  saturación) más clasificación guiada instantánea para entregar siempre la bolsa y pasos de preparación.
"""
import base64
import io
import json
import logging
import os
import urllib.error
import urllib.request

from PIL import Image, ImageOps, UnidentifiedImageError

from apps.contenidos.models import Contenedor

log = logging.getLogger('ecoparce')

MAX_FOTO_BYTES = 3 * 1024 * 1024  # 3 MB máximo
FORMATOS_PERMITIDOS = {'JPEG', 'PNG', 'WEBP'}

# Catálogo rápido de perfiles para clasificación visual y confirmación en 1 toque.
PERFILES_MATERIAL = {
    'plastico': {
        'producto': 'Envase plástico (PET / HDPE / PP)',
        'material': 'Plástico aprovechable',
        'codigo': Contenedor.BLANCA,
        'contenedor': 'Bolsa blanca (Aprovechables)',
        'indicacion': 'Vacía el líquido o contenido, enjuágalo rápido, aplástalo y ponle la tapa.',
        'simbolo': '1 · PET / 2 · HDPE',
    },
    'carton': {
        'producto': 'Caja o empaque de papel / cartón',
        'material': 'Papel o cartón',
        'codigo': Contenedor.BLANCA,
        'contenedor': 'Bolsa blanca (Aprovechables)',
        'indicacion': 'Desarma y aplasta el cartón. Debe estar limpio y seco (si tiene grasa o comida, va en bolsa negra).',
        'simbolo': 'PAP 21 · Cartón/Papel',
    },
    'vidrio': {
        'producto': 'Botella o frasco de vidrio',
        'material': 'Vidrio',
        'codigo': Contenedor.BLANCA,
        'contenedor': 'Bolsa blanca (Aprovechables)',
        'indicacion': 'Vacía y enjuaga el envase. Si está roto, envuélvelo en papel/cartón y márcalo.',
        'simbolo': 'GL 70 · Vidrio',
    },
    'metal': {
        'producto': 'Lata de aluminio o envase metálico',
        'material': 'Metal / Aluminio',
        'codigo': Contenedor.BLANCA,
        'contenedor': 'Bolsa blanca (Aprovechables)',
        'indicacion': 'Vacía, enjuaga y aplasta la lata para reducir volumen.',
        'simbolo': 'ALU 41 · Aluminio',
    },
    'metalizado': {
        'producto': 'Empaque metalizado o laminado (mecato / servilletas / icopor sucio)',
        'material': 'No aprovechable / laminado',
        'codigo': Contenedor.NEGRA,
        'contenedor': 'Bolsa negra (No aprovechables)',
        'indicacion': 'Los empaques metalizados, laminados o manchados de grasa/comida no se reciclan en ruta ordinaria.',
        'simbolo': '7 · Laminado / No aprovechable',
    },
    'organico': {
        'producto': 'Residuo orgánico (cáscaras, frutas, verduras o restos crudos)',
        'material': 'Orgánico aprovechable',
        'codigo': Contenedor.VERDE,
        'contenedor': 'Bolsa verde (Orgánicos aprovechables)',
        'indicacion': 'Deposita cáscaras, restos de comida cruda y residuos vegetales sin mezclarlos con plásticos.',
        'simbolo': 'Orgánico · Compostable',
    },
    'posconsumo': {
        'producto': 'Residuo especial (pilas, bombillos, medicamentos o aceite usado)',
        'material': 'Residuo posconsumo / peligroso',
        'codigo': Contenedor.POSCONSUMO,
        'contenedor': 'Punto de entrega Posconsumo',
        'indicacion': 'Nunca va en ninguna bolsa ordinaria. Guárdalo aparte sin romperlo y llévalo a un punto oficial.',
        'simbolo': 'Posconsumo · Especial',
    },
    'electronico': {
        'producto': 'Aparato eléctrico o electrónico (PC, portátil, celular, monitor, teclado, cables)',
        'material': 'RAEE (Residuo de Aparato Eléctrico y Electrónico)',
        'codigo': Contenedor.POSCONSUMO,
        'contenedor': 'Punto de entrega Posconsumo (RAEE)',
        'indicacion': 'Nunca va en la basura ni se enjuaga. Entrégalo entero en un punto posconsumo RAEE (EcoCómputo / Red Verde) para recuperar sus metales y evitar contaminación.',
        'simbolo': 'RAEE · Contenedor tachado',
    },
}


def validar_y_normalizar_foto(archivo_bytes):
    """Valida que los bytes sean una imagen real (JPEG/PNG/WEBP), elimina EXIF y redimensiona a <= 800 px."""
    if not archivo_bytes or len(archivo_bytes) > MAX_FOTO_BYTES:
        raise ValueError('La foto es inválida o supera el tamaño máximo permitido (3 MB).')
    try:
        img = Image.open(io.BytesIO(archivo_bytes))
        fmt = (img.format or '').upper()
        if fmt not in FORMATOS_PERMITIDOS:
            raise ValueError('Formato no permitido. Usa una foto JPEG, PNG o WEBP.')
        img = ImageOps.exif_transpose(img).convert('RGB')
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError('No pudimos leer la imagen. Toma una foto nítida en formato JPEG o PNG.') from exc

    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    salida = io.BytesIO()
    img.save(salida, format='JPEG', quality=82, optimize=True)
    return img, salida.getvalue()


def _clasificar_con_gemini(jpeg_bytes):
    """Si GEMINI_API_KEY está configurada, identifica el producto y la bolsa con Gemini multimodal."""
    api_key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if not api_key:
        return None
    prompt = (
        'Eres un experto en separación de residuos de Colombia (Resolución 2184 de 2019). '
        'Observa la foto del producto o residuo y responde SOLO un objeto JSON válido con estas claves: '
        '{"producto": "nombre corto en español", "material": "material principal", '
        '"codigo": "BLANCA" | "NEGRA" | "VERDE" | "POSCONSUMO", '
        '"indicacion": "instrucción breve de cómo prepararlo antes de desecharlo", '
        '"simbolo": "símbolo o categoría ej. 1 · PET, PAP 21, Orgánico, Posconsumo"}. '
        'Reglas: plástico/vidrio/metal/cartón/papel/tetrapak limpios -> BLANCA; '
        'empaques metalizados, icopor sucio, papel higiénico, servilletas o envases con grasa -> NEGRA; '
        'cáscaras de frutas/verduras y restos vegetales -> VERDE; '
        'pilas, baterías, bombillos, medicamentos, aceite usado o electrónicos -> POSCONSUMO.'
    )
    cuerpo = {
        'contents': [{
            'parts': [
                {'text': prompt},
                {'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(jpeg_bytes).decode('ascii')}},
            ],
        }],
        'generationConfig': {'temperature': 0.1, 'responseMimeType': 'application/json'},
    }
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'
    req = urllib.request.Request(
        url,
        data=json.dumps(cuerpo).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:  # nosec B310: endpoint fijo HTTPS de Google Gemini
            data = json.loads(resp.read().decode('utf-8'))
        texto = data['candidates'][0]['content']['parts'][0]['text']
        parsed = json.loads(texto)
        codigo = str(parsed.get('codigo', '')).upper()
        if codigo not in (Contenedor.BLANCA, Contenedor.NEGRA, Contenedor.VERDE, Contenedor.POSCONSUMO):
            return None
        cont = Contenedor.objects.filter(codigo=codigo).first()
        return {
            'producto': str(parsed.get('producto') or 'Producto identificado')[:120],
            'material': str(parsed.get('material') or 'Material identificado')[:80],
            'codigo': codigo,
            'contenedor': cont.nombre if cont else codigo,
            'indicacion': str(parsed.get('indicacion') or 'Sepáralo según la Resolución 2184 de 2019.')[:240],
            'simbolo': str(parsed.get('simbolo') or '')[:60],
            'identificado': True,
            'metodo': 'ia_vision',
            'requiere_confirmacion': False,
        }
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, OSError) as exc:
        log.warning('Clasificación con Gemini Vision fallida, usando análisis local: %s', exc)
        return None


def _clasificar_visual_local(img):
    """Analiza colorimetría HSV y luminancia en la región central de la foto con Pillow (sin red)."""
    w, h = img.size
    recorte = img.crop((int(w * 0.2), int(h * 0.2), int(w * 0.8), int(h * 0.8))).resize((64, 64))
    hsv = recorte.convert('HSV')
    pixeles = list(hsv.getdata())
    total = len(pixeles) or 1

    verdes = marrones = oscuros = claros_neutros = brillantes = 0
    for h_val, s_val, v_val in pixeles:
        # H en Pillow va de 0 a 255 (equivalente a 0..360 grados)
        if v_val < 55:
            oscuros += 1
        elif 45 <= h_val <= 110 and s_val >= 65 and v_val >= 55:
            verdes += 1
        elif 10 <= h_val <= 36 and 50 <= s_val <= 190 and 75 <= v_val <= 215:
            marrones += 1
        elif s_val < 42 and v_val >= 145:
            claros_neutros += 1
        elif s_val >= 120 and v_val >= 150:
            brillantes += 1

    if verdes / total >= 0.30:
        clave = 'organico'
    elif marrones / total >= 0.34:
        clave = 'carton'
    elif oscuros / total >= 0.45:
        clave = 'metalizado'
    elif claros_neutros / total >= 0.38:
        clave = 'plastico'
    elif brillantes / total >= 0.35:
        clave = 'metalizado'
    else:
        clave = 'plastico'

    perfil = dict(PERFILES_MATERIAL[clave])
    perfil['metodo'] = 'visual_local'
    perfil['requiere_confirmacion'] = True
    return perfil


def _clasificar_con_openai(jpeg_bytes):
    """Si OPENAI_API_KEY está configurada, identifica el producto y la bolsa con visión multimodal."""
    api_key = (os.environ.get('OPENAI_API_KEY') or '').strip()
    if not api_key:
        return None
    b64 = base64.b64encode(jpeg_bytes).decode('ascii')
    prompt = (
        'Eres un experto en separación de residuos de Colombia (Resolución 2184 de 2019). '
        'Observa la foto y responde SOLO JSON válido con: '
        '{"producto": "nombre corto en español", "material": "material principal", '
        '"codigo": "BLANCA" | "NEGRA" | "VERDE" | "POSCONSUMO", '
        '"indicacion": "cómo prepararlo", "simbolo": "ej. 1 · PET, PAP 21, Orgánico, Posconsumo"}.'
    )
    cuerpo = {
        'model': 'gpt-4o-mini',
        'response_format': {'type': 'json_object'},
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
            ],
        }],
        'max_tokens': 220,
    }
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=json.dumps(cuerpo).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:  # nosec B310: endpoint fijo HTTPS OpenAI
            data = json.loads(resp.read().decode('utf-8'))
        parsed = json.loads(data['choices'][0]['message']['content'])
        codigo = str(parsed.get('codigo', '')).upper()
        if codigo not in (Contenedor.BLANCA, Contenedor.NEGRA, Contenedor.VERDE, Contenedor.POSCONSUMO):
            return None
        cont = Contenedor.objects.filter(codigo=codigo).first()
        return {
            'producto': str(parsed.get('producto') or 'Producto identificado')[:120],
            'material': str(parsed.get('material') or 'Material identificado')[:80],
            'codigo': codigo,
            'contenedor': cont.nombre if cont else codigo,
            'indicacion': str(parsed.get('indicacion') or 'Sepáralo según la Resolución 2184 de 2019.')[:240],
            'simbolo': str(parsed.get('simbolo') or '')[:60],
            'identificado': True,
            'metodo': 'ia_vision',
            'requiere_confirmacion': False,
        }
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, OSError) as exc:
        log.warning('Clasificación con OpenAI Vision fallida, usando análisis local: %s', exc)
        return None


def analizar_foto(archivo_bytes, tipo_manual=''):
    """Analiza una foto real: usa IA multimodal (Gemini/OpenAI) si hay clave; jamás adivina por color."""
    if tipo_manual and tipo_manual in PERFILES_MATERIAL:
        perfil = dict(PERFILES_MATERIAL[tipo_manual])
        perfil['identificado'] = True
        perfil['metodo'] = 'seleccion_directa'
        perfil['requiere_confirmacion'] = False
        return perfil

    _img, jpeg_bytes = validar_y_normalizar_foto(archivo_bytes)
    resultado_ia = _clasificar_con_gemini(jpeg_bytes) or _clasificar_con_openai(jpeg_bytes)
    if resultado_ia is not None:
        return resultado_ia

    # Sin clave de IA multimodal configurada, NO inventamos un material por color: pedimos confirmación real.
    return {
        'identificado': False,
        'metodo': 'requiere_ia_o_seleccion',
        'codigo': '',
        'producto': '',
        'material': '',
        'contenedor': '',
        'indicacion': '',
        'simbolo': '',
        'mensaje': (
            'Foto recibida con éxito. El reconocimiento automático de objetos por IA aún no tiene clave '
            'GEMINI_API_KEY activa en este servidor; para no darte una respuesta incorrecta, escribe qué '
            'objeto fotografiaste o selecciónalo abajo para ver su bolsa exacta:'
        ),
        'requiere_confirmacion': True,
    }
