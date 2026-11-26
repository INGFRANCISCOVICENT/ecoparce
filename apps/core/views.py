from django.shortcuts import render

from apps.contenidos.models import Contenedor, Guia, TipoGuia


def inicio(request):
    contenedores = {c.codigo: c for c in Contenedor.objects.all()}
    guias = {g.contenedor_id: g for g in Guia.publicadas.filter(tipo=TipoGuia.SEPARACION, contenedor__isnull=False)}
    bolsas = [(c, guias.get(c.pk)) for c in contenedores.values() if c.es_bolsa]
    contexto = {
        'bolsas': bolsas,
        'posconsumo': contenedores.get(Contenedor.POSCONSUMO),
        'manejo': Guia.publicadas.filter(tipo=TipoGuia.MANEJO)[:3],
    }
    if request.user.is_authenticated:
        from apps.trivia.models import obtener_insignias, progreso_niveles
        prog = progreso_niveles(usuario=request.user)
        insignias = obtener_insignias(usuario=request.user)
        nivel_max = max(nv for nv, ok in prog['desbloqueados'].items() if ok)
        contexto.update({
            'mi_puntos': prog['puntos_totales'],
            'mi_partidas': prog['partidas_totales'],
            'mi_nivel': nivel_max,
            'mi_insignias': sum(1 for i in insignias if i['obtenida']),
            'total_insignias': len(insignias),
            'mi_sugerencias': request.user.sugerencias.count(),
        })
    return render(request, 'core/inicio.html', contexto)


def privacidad(request):
    return render(request, 'core/privacidad.html')


def terminos(request):
    return render(request, 'core/terminos.html')


def licencias(request):
    return render(request, 'core/licencias.html')


def offline(request):
    """Guía rápida offline de la Resolución 2184 de 2019 para el Service Worker PWA."""
    return render(request, 'core/offline.html')


def service_worker(request):
    """Service Worker PWA servido en raíz (/sw.js) con caché segura (excluye panel, cuenta y API)."""
    from django.http import HttpResponse
    from apps.core.context_processors import app_version
    ver = app_version()
    js = f"""/* EcoParce PWA Service Worker v{ver} */
const CACHE = 'ecoparce-pwa-{ver}';
const PRECACHE = [
  '/offline/',
  '/static/css/ecoparce.css?v={ver}',
  '/static/js/ecoparce.js?v={ver}',
  '/static/img/logo-96.png',
  '/static/img/logo-256.png',
  '/static/manifest.webmanifest'
];
const NO_CACHE_PREFIX = ['/panel/', '/cuenta/', '/accounts/', '/api/'];

self.addEventListener('install', (event) => {{
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', (event) => {{
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (NO_CACHE_PREFIX.some((p) => url.pathname.startsWith(p))) return;

  if (url.pathname.startsWith('/static/')) {{
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((resp) => {{
        if (resp.ok) {{
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }}
        return resp;
      }}))
    );
    return;
  }}

  if (req.mode === 'navigate') {{
    event.respondWith(
      fetch(req).catch(() => caches.match('/offline/'))
    );
  }}
}});
"""
    resp = HttpResponse(js, content_type='application/javascript; charset=utf-8')
    resp['Service-Worker-Allowed'] = '/'
    resp['Cache-Control'] = 'no-cache, must-revalidate'
    return resp


def version_json(request):
    """Devuelve la versión activa en servidor sin caché para avisar actualizaciones en móvil/PC."""
    from django.http import JsonResponse
    from apps.core.context_processors import app_version
    resp = JsonResponse({'version': app_version()})
    resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


def health(request):
    """Healthcheck de producción: verifica conectividad real a la base de datos."""
    from django.db import connection
    from django.http import JsonResponse
    from apps.core.context_processors import app_version
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
        resp = JsonResponse({'status': 'ok', 'version': app_version()})
    except Exception:
        resp = JsonResponse({'status': 'error'}, status=503)
    resp['Cache-Control'] = 'no-store'
    return resp


def _parsear_changelog():
    """Lee CHANGELOG.md y devuelve una lista estructurada por versión para el panel admin."""
    import re
    from django.conf import settings
    ruta = settings.BASE_DIR / 'CHANGELOG.md'
    if not ruta.exists():
        return []
    versiones = []
    actual = None
    categoria = ''
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        m_ver = re.match(r'^##\s+\[([^\]]+)\]\s*-\s*(.+)$', linea.strip())
        if m_ver:
            actual = {'version': m_ver.group(1), 'fecha': m_ver.group(2).strip(), 'cambios': []}
            versiones.append(actual)
            categoria = ''
            continue
        if actual is None:
            continue
        m_cat = re.match(r'^###\s+(.+)$', linea.strip())
        if m_cat:
            categoria = m_cat.group(1).strip()
            continue
        m_item = re.match(r'^\s*-\s+(.+)$', linea)
        if m_item:
            texto = re.sub(r'\*\*([^*]+)\*\*', r'\1', m_item.group(1).strip())
            actual['cambios'].append({'categoria': categoria or 'Cambio', 'texto': texto})
    return versiones


from apps.core.permisos import panel_requerido  # noqa: E402


@panel_requerido
def panel_versiones(request):
    """Control de versiones visible para administradores en /panel/versiones/."""
    return render(request, 'panel/versiones.html', {
        'versiones': _parsear_changelog(),
    })


def error_404(request, exception=None):
    return render(request, 'core/404.html', status=404)


def error_500(request):
    return render(request, 'core/500.html', status=500)


def error_403(request, exception=None):
    return render(request, 'core/403.html', status=403)


def security_txt(request):
    """RFC 9116: canal para reportar vulnerabilidades de forma responsable."""
    from datetime import timedelta

    from django.conf import settings
    from django.http import HttpResponse
    from django.utils import timezone
    expira = (timezone.now() + timedelta(days=180)).strftime('%Y-%m-%dT00:00:00Z')
    texto = (f'Contact: mailto:{settings.CONTACTO_SEGURIDAD}\n'
             f'Expires: {expira}\n'
             'Preferred-Languages: es, en\n'
             f'Canonical: {settings.SITE_URL}/.well-known/security.txt\n'
             f'Policy: {settings.SITE_URL}/privacidad/\n')
    return HttpResponse(texto, content_type='text/plain; charset=utf-8')


def robots_txt(request):
    """Directivas para buscadores: indexar el sitio público y excluir panel y cuentas."""
    from django.conf import settings
    from django.http import HttpResponse
    base = settings.SITE_URL.rstrip('/')
    texto = (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /panel/\n'
        'Disallow: /cuenta/\n'
        'Disallow: /accounts/\n'
        'Disallow: /q/\n'
        f'Sitemap: {base}/sitemap.xml\n'
    )
    return HttpResponse(texto, content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    """Mapa del sitio con rutas públicas y guías publicadas (RN-01)."""
    from xml.sax.saxutils import escape

    from django.conf import settings
    from django.http import HttpResponse
    base = settings.SITE_URL.rstrip('/')
    rutas_fijas = [
        ('/', 'weekly', '1.0'),
        ('/guias/', 'weekly', '0.9'),
        ('/manejo/', 'weekly', '0.9'),
        ('/buscar/', 'weekly', '0.8'),
        ('/escanear/', 'monthly', '0.8'),
        ('/puntos/', 'weekly', '0.9'),
        ('/trivia/', 'weekly', '0.8'),
        ('/sugerencias/', 'weekly', '0.7'),
        ('/privacidad/', 'yearly', '0.3'),
        ('/terminos/', 'yearly', '0.3'),
        ('/licencias/', 'yearly', '0.3'),
    ]
    lineas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for ruta, freq, prio in rutas_fijas:
        lineas.append(f'  <url><loc>{escape(base + ruta)}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>')
    for g in Guia.publicadas.only('slug', 'actualizado_en'):
        loc = escape(base + g.get_absolute_url())
        lastmod = f'<lastmod>{g.actualizado_en.date().isoformat()}</lastmod>' if g.actualizado_en else ''
        lineas.append(f'  <url><loc>{loc}</loc>{lastmod}<changefreq>monthly</changefreq><priority>0.8</priority></url>')
    lineas.append('</urlset>\n')
    return HttpResponse('\n'.join(lineas), content_type='application/xml; charset=utf-8')
