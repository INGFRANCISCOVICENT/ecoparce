"""Escáner de productos (RF-16): código de barras → empaque → bolsa correcta.

La consulta se hace desde el servidor a las bases abiertas de Open Food Facts (alimentos), Open Beauty Facts
(cuidado personal) y Open Products Facts (otros productos). Licencia de los datos: ODbL; se cita la fuente.
El navegador del visitante nunca habla con esos servicios: no se comparte su IP ni se carga código externo.
"""
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

from apps.contenidos.models import Contenedor

log = logging.getLogger('ecoparce')

BASES = [
    ('Open Food Facts', 'https://world.openfoodfacts.org'),
    ('Open Beauty Facts', 'https://world.openbeautyfacts.org'),
    ('Open Products Facts', 'https://world.openproductsfacts.org'),
    ('Open Pet Food Facts', 'https://world.openpetfoodfacts.org'),
]
URL_UPCITEMDB = 'https://api.upcitemdb.com/prod/trial/lookup?upc={codigo}'
CAMPOS = 'product_name,product_name_es,brands,packagings,packaging_tags,packaging_materials_tags,categories_tags'
CODIGO_VALIDO = re.compile(r'^\d{8,14}$')

# Material → (código de contenedor, nombre legible, indicación). Basado en la Resolución 2184 de 2019.
MATERIALES = [
    (('metallised', 'metallized', 'metalizado', 'aluminium-film', 'mixed-plastic-film'),
     Contenedor.NEGRA, 'empaque metalizado', 'Las envolturas metalizadas no son aprovechables.'),
    (('tetra', 'multilayer', 'brick', 'multicapa', 'beverage-carton', 'composite'),
     Contenedor.BLANCA, 'multicapa (tipo tetrapak)', 'Vacíalo, enjuágalo y aplástalo.'),
    (('glass', 'vidrio'), Contenedor.BLANCA, 'vidrio', 'Vacíalo y enjuágalo. Si está roto, envuélvelo en papel.'),
    (('aluminium', 'aluminum', 'steel', 'tin', 'metal', 'aluminio', 'acero', 'lata'),
     Contenedor.BLANCA, 'metal', 'Vacíalo y enjuágalo; aplasta las latas.'),
    (('cardboard', 'paperboard', 'carton', 'paper', 'carton', 'papel'),
     Contenedor.BLANCA, 'papel o cartón', 'Debe ir limpio y seco. Si tiene grasa o comida, va en la bolsa negra.'),
    (('plastic', 'pet', 'hdpe', 'ldpe', 'pp-', 'ps-', 'polyethylene', 'polypropylene', 'plastico', 'plástico'),
     Contenedor.BLANCA, 'plástico', 'Vacíalo, enjuágalo y déjalo seco.'),
]
ESPECIALES = [(('batter', 'pila'), 'Pilas'), (('light-bulb', 'bombill', 'lamp'), 'Bombillo ahorrador'),
              (('medicine', 'medicament', 'medicamento', 'drug'), 'Medicamentos vencidos')]
PARTES = {'bottle': 'Botella', 'can': 'Lata', 'box': 'Caja', 'bag': 'Bolsa', 'cap': 'Tapa', 'lid': 'Tapa',
          'tray': 'Bandeja', 'film': 'Película', 'wrapper': 'Envoltura', 'jar': 'Frasco', 'brick': 'Caja',
          'sachet': 'Sobre', 'pot': 'Vaso', 'tub': 'Tarro', 'label': 'Etiqueta', 'seal': 'Sello', 'pouch': 'Bolsa'}


def _limpiar(tag):
    return str(tag or '').split(':', 1)[-1].lower()


# Códigos y símbolos de reciclaje impresos en la base/etiqueta del envase (ISO 11469 / Res. 2184 de 2019).
ETIQUETAS_RECICLAJE = [
    (('pet', 'pete', 'polyethylene-terephthalate', '01-pet'), '1 · PET',
     'Tereftalato de polietileno (botellas de agua, gaseosa y aceite). Es uno de los plásticos más reciclados en Colombia: vacíalo, enjuágalo y aplástalo para la bolsa blanca.'),
    (('hdpe', 'pead', 'pe-hd', 'high-density', '02-hdpe'), '2 · HDPE',
     'Polietileno de alta densidad (envases de detergente, shampoo, leche). Muy reciclable y resistente: entrégalo vacío, enjuagado y seco en la bolsa blanca.'),
    (('pvc', '03-pvc', 'polyvinyl'), '3 · PVC',
     'Policloruro de vinilo (blísters, ciertos empaques rígidos). Difícil de reciclar en recolección doméstica; consulta recicladores especializados o deposítalo en bolsa negra.'),
    (('ldpe', 'pebd', 'pe-ld', 'low-density', '04-ldpe'), '4 · LDPE',
     'Polietileno de baja densidad (bolsas flexibles, film plástico). Si está completamente limpio y seco va en bolsa blanca; si tiene comida o grasa, en bolsa negra.'),
    (('pp', 'polypropylene', 'polipropileno', '05-pp'), '5 · PP',
     'Polipropileno (tapas, vasos de yogur, envases rígidos). Aprovechable en bolsa blanca siempre que esté limpio y seco.'),
    (('ps', 'polystyrene', 'icopor', '06-ps'), '6 · PS',
     'Poliestireno / icopor (bandejas y vasos desechables). Si tiene restos de comida o grasa no es aprovechable y va en bolsa negra.'),
    (('tetra', 'multilayer', 'brick', 'multicapa', 'beverage-carton', 'composite'), 'C/PAP 84 · Multicapa',
     'Envase multicapa tipo Tetra Pak (cartón + polietileno + aluminio). En Colombia sí se recicla: vacíalo, enjuágalo, ábrelo o aplástalo y ponlo seco en la bolsa blanca.'),
    (('glass', 'vidrio'), 'GL 70 · Vidrio',
     'Vidrio 100 % reciclable infinitas veces sin perder calidad. Vacíalo y enjuágalo para la bolsa blanca; si está roto, envuélvelo en papel y márcalo.'),
    (('aluminium', 'aluminum', 'aluminio', 'alu'), 'ALU 41 · Aluminio',
     'Aluminio reciclable infinitas veces (ahorra hasta 95 % de energía). Vacía, enjuaga y aplasta la lata para la bolsa blanca.'),
    (('steel', 'tin', 'acero', 'hojalata', 'metal', 'lata'), 'FE 40 · Acero',
     'Acero u hojalata (latas de conserva). Vacía, enjuaga con cuidado de los bordes y deposita en bolsa blanca.'),
    (('cardboard', 'paperboard', 'carton', 'paper', 'papel'), 'PAP 21 · Papel/Cartón',
     'Papel o cartón reciclable. Debe ir seco, limpio y sin grasa en la bolsa blanca; si está manchado de comida va en la negra.'),
    (('metallised', 'metallized', 'metalizado', 'aluminium-film', 'mixed-plastic-film'), '7 · Laminado',
     'Empaque laminado o metalizado (paquetes de mecato/papas). No es aprovechable en recolección ordinaria: va en la bolsa negra.'),
]


def detectar_etiqueta(texto):
    t = _limpiar(texto)
    for claves, simbolo, significado in ETIQUETAS_RECICLAJE:
        if any(c in t for c in claves):
            return simbolo, significado
    return None, None


def clasificar_material(texto):
    t = _limpiar(texto)
    for claves, codigo, nombre, indicacion in MATERIALES:
        if any(c in t for c in claves):
            return codigo, nombre, indicacion
    return None


# Reglas de inferencia inteligente cuando una API externa devuelve nombre/categoría sin etiquetas de empaque.
INFERENCIA_NOMBRE = [
    (('pila', 'bateria', 'batería', 'duracell', 'energizer', 'battery'), Contenedor.POSCONSUMO, 'Producto', 'pilas o baterías',
     'No va en ninguna bolsa: llévalo a un punto posconsumo de pilas.', 'Posconsumo · Pilas'),
    (('bombill', 'led bulb', 'foco', 'fluorescente'), Contenedor.POSCONSUMO, 'Producto', 'bombillo',
     'No va en ninguna bolsa: llévalo a un punto posconsumo de luminarias.', 'Posconsumo · Luminarias'),
    (('medicament', 'tableta', 'jarabe', 'acetaminofen', 'ibuprofeno', 'capsula', 'cápsula'), Contenedor.POSCONSUMO, 'Producto', 'medicamento',
     'Lleva medicamentos vencidos o sobrantes a un Punto Azul posconsumo.', 'Posconsumo · Punto Azul'),
    (('papas', 'chips', 'doritos', 'cheetos', 'mecato', 'galleta', 'chocolatina', 'snack', 'detodito', 'tostacos', 'chocoramo', 'ponque', 'ponqué'),
     Contenedor.NEGRA, 'Envoltura', 'empaque metalizado o laminado',
     'Las envolturas metalizadas o laminadas de mecato no son aprovechables: van en la bolsa negra.', '7 · Laminado'),
    (('lata', 'can ', 'cerveza', 'atun', 'atún', 'sardina', 'salchicha', 'energy drink', 'red bull', 'monster'),
     Contenedor.BLANCA, 'Lata', 'aluminio o acero',
     'Vacía, enjuaga y aplasta la lata antes de ponerla en la bolsa blanca.', 'ALU 41 · Aluminio'),
    (('tetra', 'leche', 'jugo', 'nectar', 'néctar', 'crema de leche', 'avena', 'alqueria', 'alquería', 'alpina', 'colanta'),
     Contenedor.BLANCA, 'Caja', 'multicapa (tipo tetrapak)',
     'Vacíalo, enjuágalo, ábrelo o aplástalo y ponlo seco en la bolsa blanca.', 'C/PAP 84 · Multicapa'),
    (('vidrio', 'glass', 'frasco', 'mermelada', 'compota', 'vino', 'aceite de oliva', 'salsa'),
     Contenedor.BLANCA, 'Frasco', 'vidrio',
     'Vacíalo y enjuágalo para la bolsa blanca. Si está roto, envuélvelo en papel y márcalo.', 'GL 70 · Vidrio'),
    (('agua', 'gaseosa', 'cola', 'soda', 'refresco', 'botella', 'bottle', 'pet', 'shampoo', 'champu', 'champú', 'detergente', 'jabon', 'jabón', 'suavizante', 'yogur', 'yogurt', 'aceite'),
     Contenedor.BLANCA, 'Botella', 'plástico (PET / HDPE)',
     'Vacíalo, enjuágalo rápido, aplástalo y ponle la tapa para la bolsa blanca.', '1 · PET / 2 · HDPE'),
    (('caja', 'cereal', 'carton', 'cartón', 'papel', 'cuaderno', 'pasta', 'arroz'),
     Contenedor.BLANCA, 'Caja', 'papel o cartón',
     'Desarma y aplasta la caja limpia y seca para la bolsa blanca (si tiene grasa, va en negra).', 'PAP 21 · Cartón/Papel'),
]


def _consultar(base, codigo):
    """Consulta un código de barras en Open Food/Beauty/Products/Pet Facts API v2."""
    url = f'{base}/api/v2/product/{codigo}.json?fields={CAMPOS}'
    req = urllib.request.Request(url, headers={
        'User-Agent': f'EcoParce/2.9 ({settings.SITE_URL}; {settings.CONTACTO_SEGURIDAD})', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=6) as r:  # nosec B310: bases fijas https, código validado (solo dígitos)
        datos = json.loads(r.read().decode('utf-8'))
    return datos.get('product') if datos.get('status') == 1 else None


def _consultar_api_empresa(codigo):
    """Conector configurable a API de catálogo empresarial (EMPRESA_PRODUCTOS_API_URL + EMPRESA_PRODUCTOS_API_KEY)."""
    url_base = (os.environ.get('EMPRESA_PRODUCTOS_API_URL') or '').strip()
    if not url_base or not url_base.startswith('https://'):
        return None
    url = url_base.replace('{codigo}', urllib.parse.quote(codigo)) if '{codigo}' in url_base else f"{url_base.rstrip('/')}/{codigo}"
    headers = {'Accept': 'application/json', 'User-Agent': f'EcoParce/2.9 ({settings.SITE_URL})'}
    api_key = (os.environ.get('EMPRESA_PRODUCTOS_API_KEY') or '').strip()
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
        headers['X-API-Key'] = api_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=6) as r:  # nosec B310: URL HTTPS configurada por administrador
        data = json.loads(r.read().decode('utf-8'))
    if not isinstance(data, dict):
        return None
    nombre = data.get('nombre') or data.get('product_name') or data.get('title')
    if not nombre:
        return None
    return {
        'product_name_es': str(nombre)[:120],
        'brands': str(data.get('marca') or data.get('brand') or '')[:80],
        'packaging_tags': data.get('packaging_tags') or ([data['material']] if data.get('material') else []),
        'categories_tags': [str(data.get('categoria') or data.get('category') or '')],
    }


def _consultar_upcitemdb(codigo):
    """Consulta la base global pública UPCitemdb para productos de supermercado y consumo masivo."""
    url = URL_UPCITEMDB.format(codigo=codigo)
    req = urllib.request.Request(url, headers={
        'User-Agent': f'EcoParce/2.9 ({settings.SITE_URL})', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=6) as r:  # nosec B310: endpoint fijo HTTPS, código solo dígitos
        datos = json.loads(r.read().decode('utf-8'))
    items = datos.get('items') or []
    if not items:
        return None
    item = items[0]
    return {
        'product_name_es': (item.get('title') or '').strip()[:120],
        'brands': (item.get('brand') or '').strip()[:80],
        'packaging_tags': [],
        'categories_tags': [item.get('category') or ''],
    }


def buscar_producto(codigo):
    """Devuelve (nombre_fuente, producto) o (None, None). Consulta API empresarial, Open*Facts y UPCitemdb."""
    if not CODIGO_VALIDO.match(codigo):
        return None, None
    clave = f'producto:{codigo}'
    guardado = cache.get(clave)
    if guardado is not None:
        return tuple(guardado) if guardado else (None, None)

    # 1. API empresarial privada (si el administrador configuró EMPRESA_PRODUCTOS_API_URL)
    try:
        prod_emp = _consultar_api_empresa(codigo)
        if prod_emp:
            cache.set(clave, ['Catálogo Empresarial API', prod_emp], 60 * 60 * 24 * 7)
            return 'Catálogo Empresarial API', prod_emp
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        log.warning('Consulta de producto fallida en API Empresarial: %s', e)

    # 2. Bases abiertas globales (Open Food / Beauty / Products / Pet Facts)
    for nombre, base in BASES:
        try:
            producto = _consultar(base, codigo)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            log.warning('Consulta de producto fallida en %s: %s', nombre, e)
            continue
        if producto:
            cache.set(clave, [nombre, producto], 60 * 60 * 24 * 7)
            return nombre, producto

    # 3. Respaldo global UPCitemdb (productos comerciales y supermercados)
    try:
        prod_upc = _consultar_upcitemdb(codigo)
        if prod_upc and prod_upc.get('product_name_es'):
            cache.set(clave, ['UPCitemdb Global', prod_upc], 60 * 60 * 24 * 7)
            return 'UPCitemdb Global', prod_upc
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        log.warning('Consulta de producto fallida en UPCitemdb: %s', e)

    cache.set(clave, [], 60 * 60 * 12)
    return None, None


def analizar(producto):
    """Traduce el empaque del producto a partes con su bolsa correspondiente."""
    contenedores = {c.codigo: c for c in Contenedor.objects.all()}
    partes, vistos = [], set()
    categorias = ' '.join(producto.get('categories_tags') or [])
    for claves, residuo in ESPECIALES:
        if any(c in categorias for c in claves):
            c = contenedores[Contenedor.POSCONSUMO]
            return [{'parte': 'Producto', 'material': residuo.lower(), 'codigo': c.codigo, 'contenedor': c.nombre,
                     'indicacion': 'No va en ninguna bolsa: llévalo a un punto posconsumo.', 'residuo': residuo}]

    componentes = producto.get('packagings') or []
    for comp in componentes:
        material = comp.get('material') or ''
        forma = _limpiar(comp.get('shape'))
        resultado = clasificar_material(material) or clasificar_material(forma)
        if not resultado:
            continue
        codigo, nombre_material, indicacion = resultado
        parte = PARTES.get(forma.split('-')[0], forma.replace('-', ' ').capitalize() or 'Empaque')
        clave = (parte, codigo)
        if clave in vistos:
            continue
        vistos.add(clave)
        c = contenedores[codigo]
        simbolo, significado = detectar_etiqueta(material)
        if not simbolo:
            simbolo, significado = detectar_etiqueta(forma)
        item = {'parte': parte, 'material': nombre_material, 'codigo': codigo, 'contenedor': c.nombre, 'indicacion': indicacion}
        if simbolo:
            item['simbolo'] = simbolo
            item['significado'] = significado
        partes.append(item)

    if not partes:  # respaldo: etiquetas de empaque y de materiales
        for tag in (producto.get('packaging_materials_tags') or []) + (producto.get('packaging_tags') or []):
            resultado = clasificar_material(tag)
            if not resultado:
                continue
            codigo, nombre_material, indicacion = resultado
            t = _limpiar(tag)
            parte = next((v for k, v in PARTES.items() if k in t), 'Empaque')
            if (parte, codigo) in vistos:
                continue
            vistos.add((parte, codigo))
            c = contenedores[codigo]
            simbolo, significado = detectar_etiqueta(tag)
            item = {'parte': parte, 'material': nombre_material, 'codigo': codigo, 'contenedor': c.nombre, 'indicacion': indicacion}
            if simbolo:
                item['simbolo'] = simbolo
                item['significado'] = significado
            partes.append(item)

    if not partes:  # respaldo inteligente: inferencia por nombre, marca y categoría del producto
        texto_prod = ' '.join(
            str(producto.get(k) or '')
            for k in ('product_name_es', 'product_name', 'brands')
        ).lower() + ' ' + categorias.lower()
        for claves, codigo, parte, nombre_mat, indicacion, simbolo in INFERENCIA_NOMBRE:
            if any(c in texto_prod for c in claves):
                c = contenedores[codigo]
                item = {
                    'parte': parte,
                    'material': nombre_mat,
                    'codigo': codigo,
                    'contenedor': c.nombre,
                    'indicacion': indicacion,
                    'simbolo': simbolo,
                }
                partes.append(item)
                break
    return partes
