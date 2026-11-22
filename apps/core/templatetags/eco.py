"""Etiquetas de plantilla de EcoParce: iconos SVG en línea y utilidades de presentación."""
import re

from django import template
from django.utils.html import format_html
from django.utils.safestring import SafeString

register = template.Library()

ICONOS = {
        'menu': '<path d="M4 7h16M4 12h16M4 17h16"/>',
        'search': '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
        'home': '<path d="M4 11l8-7 8 7v9h-5v-6h-6v6H4z"/>',
        'book': '<path d="M5 4h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h10"/>',
        'game': '<rect x="3" y="7" width="18" height="11" rx="4"/><path d="M8 11v4M6 13h4M15 12h.01M18 14h.01"/>',
        'pin': '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
        'clock': '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
        'check': '<path d="M5 12l4 4 10-10"/>',
        'x': '<path d="M6 6l12 12M18 6L6 18"/>',
        'share': '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.2 11l7.6-4M8.2 13l7.6 4"/>',
        'qr': '<rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><path d="M14 14h2v2h-2zM18 18h2v2h-2zM14 18h2M18 14h2"/>',
        'chart': '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
        'users': '<circle cx="9" cy="8" r="3.5"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M21 20a6 6 0 0 0-4-5.6"/>',
        'file': '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 13h6M9 17h6"/>',
        'eye': '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
        'msg': '<path d="M4 5h16v11H9l-5 4z"/>',
        'leaf': '<path d="M5 19c0-8 5-14 15-14 0 10-6 15-14 15"/><path d="M5 19c3-4 6-7 10-9"/>',
        'battery': '<rect x="3" y="7" width="16" height="10" rx="2"/><path d="M21 10v4M6 10v4M9 10v4"/>',
        'drop': '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
        'bulb': '<path d="M9 18h6M10 21h4M8 14a6 6 0 1 1 8 0c-.8.8-1 1.5-1 2H9c0-.5-.2-1.2-1-2z"/>',
        'pill': '<rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-35 12 12)"/><path d="M9.5 8.5l5 7"/>',
        'phone': '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',
        'arrow': '<path d="M5 12h14M13 6l6 6-6 6"/>',
        'back': '<path d="M19 12H5M11 6l-6 6 6 6"/>',
        'plus': '<path d="M12 5v14M5 12h14"/>',
        'down': '<path d="M12 4v12M6 10l6 6 6-6M4 20h16"/>',
        'logout': '<path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11"/>',
        'lock': '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
        'shield': '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
        'filter': '<path d="M4 5h16l-6 8v6l-4-2v-4z"/>',
        'edit': '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
        'send': '<path d="M4 12l16-8-6 16-3-7z"/>',
        'trash': '<path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13"/>',
        'star': '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
        'copy': '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
        'whatsapp': '<path d="M4 20l1.3-4A8 8 0 1 1 8 18.7z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.5-2-1-1 .8a4 4 0 0 1-1.8-1.8l.8-1-1-2z"/>',
        'refresh': '<path d="M20 11a8 8 0 0 0-14.6-4.5M4 4v4h4M4 13a8 8 0 0 0 14.6 4.5M20 20v-4h-4"/>',
        'power': '<path d="M12 3v8M6.3 6.3a8 8 0 1 0 11.4 0"/>',
        'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
        'history': '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>',
}


@register.simple_tag
def icono(nombre, tam=22, color='currentColor', grosor=2.2):
    """Dibuja un icono de trazo (sin dependencias externas)."""
    trazo = SafeString(ICONOS.get(nombre, ICONOS['info']))  # nosec B703: trazos SVG fijos de este archivo, sin datos del usuario
    tam = int(tam) if str(tam).isdigit() else 22
    color = color if re.fullmatch(r'#[0-9A-Fa-f]{3,8}|currentColor', str(color)) else 'currentColor'
    grosor = float(grosor) if re.fullmatch(r'\d+(\.\d+)?', str(grosor)) else 2.2
    return format_html(
        '<svg class="i" width="{0}" height="{0}" viewBox="0 0 24 24" fill="none" stroke="{1}" stroke-width="{2}" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{3}</svg>', tam, color, grosor, trazo)


CLASES_ESTADO = {'PUBLICADO': 's-pub', 'EN_REVISION': 's-rev', 'BORRADOR': 's-bor', 'RETIRADO': 's-ret',
                 'PENDIENTE': 's-rev', 'ATENDIDA': 's-pub', 'DESCARTADA': 's-bor'}


@register.filter
def clase_estado(estado):
    return CLASES_ESTADO.get(estado, 's-bor')


@register.filter
def porcentaje(parte, total):
    try:
        return round(100 * parte / total) if total else 0
    except (TypeError, ZeroDivisionError):
        return 0


@register.simple_tag(takes_context=True)
def activo(context, *prefijos):
    """Devuelve «on» si la ruta actual empieza por alguno de los prefijos."""
    ruta = context['request'].path
    return 'on' if any((ruta == p) if p in ('/', '/panel/') else ruta.startswith(p) for p in prefijos) else ''


@register.simple_tag(takes_context=True)
def aria_actual(context, *prefijos):
    """Devuelve aria-current="page" cuando la ruta coincide con alguno de los prefijos."""
    return SafeString('aria-current="page"') if activo(context, *prefijos) else ''


@register.filter
def icono_residuo(nombre):
    n = (nombre or '').lower()
    for clave, ic in (('pila', 'battery'), ('bater', 'battery'), ('aceite', 'drop'), ('medic', 'pill'),
                      ('bombill', 'bulb'), ('lumin', 'bulb'), ('electr', 'phone'), ('celular', 'phone'), ('raee', 'phone')):
        if clave in n:
            return ic
    return 'battery'
