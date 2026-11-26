"""Motor conversacional del Asistente Eco (Escarlata) para EcoParce.

Arquitectura modular de procesamiento de consultas ciudadanas:
1. Detección de intenciones conversacionales (saludos, despedidas, ayuda, mapa, escáner, trivia).
2. Reglas expertas de la Resolución 2184 de 2019 (contaminación con grasa/comida, RAEE/electrónicos,
   y consultas específicas por color de bolsa).
3. Extracción de entidad desde preguntas en lenguaje natural («¿dónde boto una boteya?») y búsqueda
   tolerante a errores ortográficos en el catálogo oficial publicado (RN-01).
"""
from django.urls import reverse

from apps.core.texto import normalizar

_RELLENO_CONVERSACIONAL = {
    'donde', 'adonde', 'en', 'que', 'cual', 'como', 'boto', 'botar', 'tiro', 'tirar',
    'pongo', 'poner', 'echo', 'echar', 'va', 'van', 'debo', 'debe', 'puedo', 'reciclo',
    'reciclar', 'separo', 'separar', 'tengo', 'quiero', 'una', 'uno', 'unas', 'unos',
    'el', 'la', 'los', 'las', 'de', 'del', 'al', 'mi', 'mis', 'su', 'un', 'bolsa',
    'caneca', 'basura', 'residuo', 'residuos', 'viejo', 'vieja', 'usado', 'usada',
    'roto', 'rota', 'hola', 'por', 'favor', 'dime', 'sabes', 'es', 'son', 'para',
}


def _extraer_nucleo(qn):
    """Elimina palabras de relleno de una pregunta natural para aislar el residuo buscado."""
    palabras = [p for p in qn.split() if len(p) >= 2 and p not in _RELLENO_CONVERSACIONAL]
    return ' '.join(palabras)


def _respuesta_intencion(qn):
    """Detecta saludos, agradecimientos, dudas de uso o reglas expertas de la Res. 2184."""
    palabras = set(qn.split())

    # 1. Saludos
    if palabras & {'hola', 'buenas', 'buenos', 'hey', 'saludos'} and len(palabras) <= 4:
        return {
            'encontrado': True,
            'residuo': '¡Hola! Soy Escarlata, tu asistente de reciclaje',
            'contenedor': 'Resolución 2184 de 2019 · Colombia',
            'codigo': 'VERDE',
            'pasos': [
                'Pregúntame por cualquier residuo (ej. «caja de pizza con grasa», «computador», «aceite usado»).',
                'También puedo guiarte al escáner de fotos/QR, al mapa de puntos posconsumo o a la trivia.',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Explorar guías de colores',
            'puntos_url': reverse('contenidos:puntos'),
            'relacionados': ['Botella PET', 'Caja de pizza', 'Computador', 'Aceite usado'],
        }

    # 2. Agradecimientos
    if palabras & {'gracias', 'excelente', 'genial', 'perfecto', 'super', 'listo'} and len(palabras) <= 4:
        return {
            'encontrado': True,
            'residuo': '¡Con mucho gusto!',
            'contenedor': 'Cada residuo bien separado cuenta',
            'codigo': 'VERDE',
            'pasos': [
                'Si tienes otra duda sobre algún empaque o residuo, escríbeme cuando quieras.',
            ],
            'guia_url': reverse('trivia:inicio'),
            'guia_titulo': 'Pon a prueba lo aprendido en la Trivia',
            'puntos_url': '',
            'relacionados': ['Res. 2184', 'Pilas', 'Tetra Pak'],
        }

    # 3. Regla crítica de contaminación con grasa o comida (error #1 en casa)
    if any(p in qn for p in ('pizza', 'con grasa', 'engrasad', 'manchad', 'con comida', 'sucio', 'sucia')):
        return {
            'encontrado': True,
            'residuo': 'Empaque, cartón o papel con grasa o comida',
            'contenedor': 'Bolsa negra (No aprovechables)',
            'codigo': 'NEGRA',
            'pasos': [
                'La grasa y los restos de comida contaminan el papel y el cartón reciclable.',
                'Si una caja de pizza tiene la tapa limpia, puedes arrancar la tapa para bolsa blanca y enviar la base engrasada a bolsa negra.',
                'Antes de desechar el empaque, retira las sobras orgánicas a la bolsa verde.',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Ver guía de Bolsa Negra',
            'puntos_url': '',
            'relacionados': ['Servilletas', 'Icopor', 'Cartón limpio'],
        }

    # 4. Aparatos electrónicos / RAEE (PC, celular, monitor, cables, electrodomésticos)
    if any(p in qn for p in ('computador', 'portatil', 'laptop', 'monitor', 'teclado', 'mouse', 'cargador', 'celular', 'televisor', 'raee', 'electronico', 'electrodomestico')):
        return {
            'encontrado': True,
            'residuo': 'Aparato eléctrico o electrónico (RAEE)',
            'contenedor': 'Punto de entrega Posconsumo',
            'codigo': 'POSCONSUMO',
            'es_especial': True,
            'pasos': [
                'Nunca va en bolsa blanca, negra ni verde, ni se debe mojar o desarmar en casa.',
                'Contiene metales recuperables y componentes que contaminan si llegan al relleno sanitario.',
                'Entrégalo entero en un punto posconsumo oficial (EcoCómputo / Red Verde).',
            ],
            'guia_url': reverse('contenidos:manejo'),
            'guia_titulo': 'Ver guía de residuos especiales',
            'puntos_url': reverse('contenidos:puntos'),
            'relacionados': ['Pilas', 'Bombillos', 'Aceite usado'],
        }

    # 5. Consultas específicas sobre cada bolsa o la Resolución 2184
    if 'bolsa blanca' in qn:
        return {
            'encontrado': True,
            'residuo': 'Bolsa Blanca · Residuos Aprovechables',
            'contenedor': 'Bolsa blanca (Aprovechables)',
            'codigo': 'BLANCA',
            'pasos': [
                'Sí va: plástico (botellas PET, envases), vidrio, cartón, papel, latas y Tetra Pak.',
                'Regla de oro: todo debe ir vacío, limpio, enjuagado y seco.',
                'No va: servilletas usadas, cartón con grasa ni empaques metalizados.',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Ver guía completa de Bolsa Blanca',
            'puntos_url': '',
            'relacionados': ['Botella PET', 'Tetra Pak', 'Vidrio'],
        }
    if 'bolsa negra' in qn:
        return {
            'encontrado': True,
            'residuo': 'Bolsa Negra · Residuos No Aprovechables',
            'contenedor': 'Bolsa negra (No aprovechables)',
            'codigo': 'NEGRA',
            'pasos': [
                'Sí va: papel higiénico, servilletas sucias, pañales, empaques metalizados de mecato, icopor sucio y cartón con grasa.',
                'Cierra muy bien la bolsa para evitar derrames o malos olores.',
                'Nunca mezcles pilas, bombillos, medicamentos ni aceite aquí.',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Ver guía completa de Bolsa Negra',
            'puntos_url': '',
            'relacionados': ['Icopor', 'Caja de pizza', 'Servilletas'],
        }
    if 'bolsa verde' in qn:
        return {
            'encontrado': True,
            'residuo': 'Bolsa Verde · Orgánicos Aprovechables',
            'contenedor': 'Bolsa verde (Orgánicos aprovechables)',
            'codigo': 'VERDE',
            'pasos': [
                'Sí va: cáscaras de frutas y verduras, restos de comida cruda, cuncho de café y residuos de poda.',
                'Estos residuos sirven para hacer compostaje y abono natural.',
                'No mezcles bolsas plásticas, vidrio ni aceite de cocina.',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Ver guía completa de Bolsa Verde',
            'puntos_url': '',
            'relacionados': ['Cáscaras', 'Cuncho de café', 'Res. 2184'],
        }
    if any(p in qn for p in ('2184', 'resolucion', 'codigo de colores')):
        return {
            'encontrado': True,
            'residuo': 'Código de colores en Colombia (Res. 2184 de 2019)',
            'contenedor': 'Blanca · Negra · Verde · Posconsumo',
            'codigo': 'VERDE',
            'pasos': [
                'Bolsa Blanca: aprovechables limpios y secos (plástico, vidrio, cartón, papel, metales).',
                'Bolsa Negra: no aprovechables (servilletas, papel higiénico, cartón con grasa).',
                'Bolsa Verde: orgánicos aprovechables (cáscaras, restos de comida cruda, cuncho de café).',
                'Posconsumo: pilas, aceite usado, bombillos, medicamentos vencidos y electrónicos (RAEE).',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Ver todas las guías oficiales',
            'puntos_url': reverse('contenidos:puntos'),
            'relacionados': ['Bolsa blanca', 'Bolsa negra', 'Bolsa verde'],
        }

    # 6. Navegación rápida por herramientas de EcoParce
    if any(p in qn for p in ('mapa', 'punto cercano', 'puntos oficiales', 'donde entregar', 'donde llevar')):
        return {
            'encontrado': True,
            'residuo': 'Mapa de Puntos Posconsumo Oficiales',
            'contenedor': 'Puntos de entrega en Bogotá (SDA)',
            'codigo': 'POSCONSUMO',
            'pasos': [
                'Consulta más de 1.800 puntos oficiales para entregar pilas, aceite usado, bombillos, medicamentos y RAEE.',
                'Puedes filtrar por localidad o activar tu ubicación para ver los más cercanos.',
            ],
            'guia_url': reverse('contenidos:puntos'),
            'guia_titulo': 'Abrir mapa de puntos',
            'puntos_url': '',
            'relacionados': ['Pilas', 'Aceite usado', 'Computador'],
        }
    if any(p in qn for p in ('escanear', 'escaner', 'tomar foto', 'codigo de barras', 'qr')):
        return {
            'encontrado': True,
            'residuo': 'Escáner de Productos por Foto, Barras y QR',
            'contenedor': 'Herramienta interactiva EcoParce',
            'codigo': 'BLANCA',
            'pasos': [
                'Apunta al código de barras o QR del empaque, o toma una foto directa del objeto.',
                'Te indicaremos qué material es y en qué bolsa va según la Resolución 2184.',
            ],
            'guia_url': reverse('buscador:escanear'),
            'guia_titulo': 'Abrir escáner ahora',
            'puntos_url': '',
            'relacionados': ['Botella PET', 'Tetra Pak', 'Computador'],
        }
    if any(p in qn for p in ('trivia', 'juego', 'jugar', 'medalla', 'certificado', 'diploma')):
        return {
            'encontrado': True,
            'residuo': 'Trivia Ecológica, Arcade y Medallas 3D',
            'contenedor': 'Aprende jugando en EcoParce',
            'codigo': 'VERDE',
            'pasos': [
                'Juega 3 modos de trivia, supera niveles, desbloquea medallas 3D y descarga tu certificado ambiental.',
            ],
            'guia_url': reverse('trivia:inicio'),
            'guia_titulo': 'Ir a la Trivia',
            'puntos_url': '',
            'relacionados': ['Res. 2184', 'Bolsa blanca', 'Bolsa verde'],
        }
    if any(p in qn for p in ('ayuda', 'como funciona', 'quien eres', 'que puedes hacer')):
        return {
            'encontrado': True,
            'residuo': '¿Cómo puedo ayudarte?',
            'contenedor': 'Asistente Eco · Escarlata',
            'codigo': 'VERDE',
            'pasos': [
                'Escríbeme cualquier objeto (incluso con errores de escritura) y te diré la bolsa exacta.',
                'Puedo explicarte cada bolsa de la Resolución 2184, ubicar puntos posconsumo o llevarte al escáner.',
            ],
            'guia_url': reverse('contenidos:guias'),
            'guia_titulo': 'Ver guías de separación',
            'puntos_url': reverse('contenidos:puntos'),
            'relacionados': ['Bolsa blanca', 'Caja de pizza', 'Computador'],
        }
    return None


def responder_consulta(q, buscar_fn):
    """Resuelve cualquier consulta ciudadana combinando intenciones expertas y catálogo oficial."""
    qn = normalizar(q)
    directa = _respuesta_intencion(qn)
    if directa is not None:
        return directa

    # Buscar primero por frase completa; si no hay coincidencia, extraer el núcleo quitando palabras de relleno.
    resultados = buscar_fn(q)
    if not resultados:
        nucleo = _extraer_nucleo(qn)
        if nucleo and nucleo != qn:
            resultados = buscar_fn(nucleo)

    if resultados:
        principal = resultados[0]
        guia_pub = principal.guia if principal.guia and principal.guia.publicado else None
        return {
            'encontrado': True,
            'residuo': principal.nombre,
            'contenedor': principal.contenedor.nombre,
            'codigo': principal.contenedor.codigo,
            'es_especial': principal.es_especial,
            'pasos': principal.pasos[:4] or [
                'Verifica que el residuo esté separado correctamente antes de entregarlo.'
            ],
            'guia_url': guia_pub.get_absolute_url() if guia_pub else reverse('contenidos:guias'),
            'guia_titulo': f'Ver guía: {guia_pub.titulo}' if guia_pub else 'Ver guías de separación',
            'puntos_url': f"{reverse('contenidos:puntos')}?residuo={principal.pk}" if principal.es_especial else '',
            'relacionados': [r.nombre for r in resultados[1:4]],
        }

    return {
        'encontrado': False,
        'mensaje': (
            f'No encontré «{q}» exacto en nuestro catálogo todavía. '
            'Regla práctica: si es plástico/vidrio/cartón/metal limpio y seco va en bolsa blanca; '
            'si tiene grasa o comida, en bolsa negra; si es orgánico, en bolsa verde; '
            'si es pila, bombillo, aceite o electrónico, en punto posconsumo.'
        ),
        'buscar_url': f"{reverse('buscador:buscar')}?q={q}",
        'sugerir_url': reverse('buscador:sugerir'),
    }
