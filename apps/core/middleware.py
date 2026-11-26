class CabecerasSeguridadMiddleware:
    """Cabeceras de endurecimiento OWASP (RNF-02): CSP estricta, Permissions-Policy y aislamiento."""
    CSP = (
        "default-src 'self'; "
        "img-src 'self' data: blob: https://tile.openstreetmap.org; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "worker-src 'self'; "
        "manifest-src 'self'; "
        "object-src 'none'; "
        "form-action 'self' https://accounts.google.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        csp = self.CSP + ('; upgrade-insecure-requests' if request.is_secure() else '')
        respuesta.setdefault('Content-Security-Policy', csp)
        respuesta.setdefault(
            'Permissions-Policy',
            'camera=(self), microphone=(self), geolocation=(self), payment=(), usb=(), '
            'magnetometer=(), gyroscope=(), accelerometer=(), interest-cohort=()',
        )
        respuesta.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        respuesta.setdefault('X-Permitted-Cross-Domain-Policies', 'none')
        respuesta.setdefault('X-DNS-Prefetch-Control', 'off')
        if request.path.startswith(('/panel/', '/cuenta/', '/accounts/', '/api/')):
            respuesta['Cache-Control'] = 'no-store'
        elif 'text/html' in (respuesta.get('Content-Type') or ''):
            respuesta.setdefault('Cache-Control', 'no-cache, must-revalidate')
        return respuesta
