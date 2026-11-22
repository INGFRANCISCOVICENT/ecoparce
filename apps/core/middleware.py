class CabecerasSeguridadMiddleware:
    """Cabeceras adicionales (RNF-02): política de contenido y permisos del navegador.
    form-action admite accounts.google.com porque el ingreso con Google es un POST que redirige allá
    (Chrome aplica form-action también a las redirecciones)."""
    CSP = ("default-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; style-src 'self' 'unsafe-inline'; script-src 'self'; "
           "font-src 'self'; connect-src 'self'; form-action 'self' https://accounts.google.com; frame-ancestors 'none'; base-uri 'self'")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.setdefault('Content-Security-Policy', self.CSP)
        respuesta.setdefault('Permissions-Policy', 'camera=(self), microphone=(), geolocation=(self), interest-cohort=()')
        respuesta.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        if request.path.startswith(('/panel/', '/cuenta/', '/accounts/')):
            respuesta['Cache-Control'] = 'no-store'
        return respuesta
