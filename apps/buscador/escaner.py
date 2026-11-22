"""Escáner de productos (RF-16): código de barras → empaque → bolsa correcta.

La consulta se hace desde el servidor a las bases abiertas de Open Food Facts (alimentos), Open Beauty Facts
(cuidado personal) y Open Products Facts (otros productos). Licencia de los datos: ODbL; se cita la fuente.
El navegador del visitante nunca habla con esos servicios: no se comparte su IP ni se carga código externo.
"""
import json
import logging
import re
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

from apps.contenidos.models import Contenedor

log = logging.getLogger('ecoparce')

BASES = [
    ('Open Food Facts', 'https://world.openfoodfacts.org'),
    ('Open Beauty Facts', 'https://world.openbeautyfacts.org'),
    ('Open Products Facts', 'https://world.openproductsfacts.org'),
]
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


def _consultar(base, codigo):
    url = f'{base}/api/v2/product/{codigo}.json?fields={CAMPOS}'
    req = urllib.request.Request(url, headers={
        'User-Agent': f'EcoParce/1.2 ({settings.SITE_URL}; {settings.CONTACTO_SEGURIDAD})', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=6) as r:  # nosec B310: bases fijas https, código validado (solo dígitos)
        datos = json.loads(r.read().decode('utf-8'))
    return datos.get('product') if datos.get('status') == 1 else None


def buscar_producto(codigo):
    """Devuelve (nombre_fuente, producto) o (None, None). Usa caché para no repetir consultas."""
    if not CODIGO_VALIDO.match(codigo):
        return None, None
    clave = f'producto:{codigo}'
    guardado = cache.get(clave)
    if guardado is not None:
        return tuple(guardado) if guardado else (None, None)
    for nombre, base in BASES:
        try:
            producto = _consultar(base, codigo)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            log.warning('Consulta de producto fallida en %s: %s', nombre, e)
            continue
        if producto:
            cache.set(clave, [nombre, producto], 60 * 60 * 24 * 7)
            return nombre, producto
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
    return partes
