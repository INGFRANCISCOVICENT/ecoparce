"""Datos de apoyo para las pruebas automatizadas."""
from apps.contenidos.models import Contenedor, EstadoContenido, Guia, Residuo
from apps.cuentas.models import Rol, Usuario

CLAVE = 'Clave-de-prueba-2026'


def usuarios():
    from django.core.cache import cache
    cache.clear()
    sistema = Usuario.objects.create_user('sistema@ecoparce.com.co', 'Francisco Navarro', CLAVE, rol=Rol.SISTEMA)
    autor = Usuario.objects.create_user('autor@ecoparce.com.co', 'Danixa Herrera', CLAVE, rol=Rol.CONTENIDO)
    revisor = Usuario.objects.create_user('revisor@ecoparce.com.co', 'Darien García', CLAVE, rol=Rol.CONTENIDO)
    return sistema, autor, revisor


def guia(autor, revisor=None, estado=EstadoContenido.PUBLICADO, codigo='BLANCA', **extra):
    datos = dict(titulo='Bolsa blanca: aprovechables', tipo='SEPARACION', resumen='Limpios y secos',
                 cuerpo='Texto.\n+ Botellas\n- Servilletas', contenedor=Contenedor.objects.get(codigo=codigo),
                 fuente_oficial='Resolución 2184 de 2019', autor=autor, revisor=revisor, estado=estado)
    datos.update(extra)
    return Guia.objects.create(**datos)


def residuo(nombre, autor, revisor=None, codigo='BLANCA', estado=EstadoContenido.PUBLICADO, **extra):
    return Residuo.objects.create(nombre=nombre, contenedor=Contenedor.objects.get(codigo=codigo), autor=autor,
                                  revisor=revisor, estado=estado, es_especial=codigo == 'POSCONSUMO', **extra)


def consentir(*usuarios_):
    from django.conf import settings

    from apps.cuentas.models import Consentimiento
    for u in usuarios_:
        Consentimiento.objects.get_or_create(usuario=u, version=settings.VERSION_AVISO_PRIVACIDAD)


def activar_totp(usuario):
    """Crea un autenticador TOTP real (secreto cifrado) y devuelve el secreto en claro."""
    from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret
    secreto = generate_totp_secret()
    TOTP.activate(usuario, secreto)
    return secreto


def codigo_totp(secreto):
    from allauth.mfa.totp.internal.auth import hotp_value, format_hotp_value
    import time as _t
    return format_hotp_value(hotp_value(secreto, int(_t.time() // 30)))


def entrar_panel(client, usuario, mfa=True, metodo='socialaccount'):
    """Simula una sesión de administrador que ya pasó por Google y por la verificación en dos pasos."""
    import time as _t

    from allauth.mfa.models import Authenticator
    consentir(usuario)
    if mfa and not Authenticator.objects.filter(user=usuario, type='totp').exists():
        activar_totp(usuario)
    client.force_login(usuario)
    sesion = client.session
    ahora = _t.time()
    registros = [{'method': metodo, 'at': ahora, 'provider': 'google'}]
    if mfa:
        registros.append({'method': 'mfa', 'at': ahora, 'type': 'totp'})
    sesion['account_authentication_methods'] = registros
    sesion['account_authentication_methods_user'] = str(usuario.pk)
    sesion.save()


def reautenticar(client, usuario):
    """Marca que el administrador acaba de confirmar su identidad con TOTP (acciones sensibles)."""
    import time as _t
    sesion = client.session
    registros = list(sesion.get('account_authentication_methods', []))
    registros.append({'method': 'mfa', 'at': _t.time(), 'type': 'totp', 'reauthenticated': True})
    sesion['account_authentication_methods'] = registros
    sesion.save()
