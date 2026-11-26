"""Cifrado autenticado a nivel de campo para datos sensibles en la base de datos (OWASP A02 / Ley 1581).

Usa MultiFernet (AES-128-CBC + HMAC-SHA256) con soporte de rotación de claves:
- En producción utiliza DB_CLAVE_CIFRADO (con respaldo en MFA_CLAVE_CIFRADO) y opcionalmente
  DB_CLAVE_CIFRADO_ANTERIOR para descifrar registros cifrados con la clave previa.
- En desarrollo local, si MFA_CLAVE_DERIVADA_DESARROLLO está activo, deriva una clave
  determinística a partir de SECRET_KEY.
- Es idempotente y retrocompatible: los valores cifrados llevan el prefijo ``enc:f1:``;
  los registros heredados en texto plano se leen sin error y se cifran al guardarse.
"""
import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

PREFIJO_CIFRADO = 'enc:f1:'


def _obtener_fernet():
    """Construye un MultiFernet con las claves vigentes y anteriores para soportar rotación sin pérdida."""
    claves = []
    for nombre in ('DB_CLAVES_CIFRADO', 'MFA_CLAVES_CIFRADO'):
        for clave in getattr(settings, nombre, []) or []:
            if clave and clave not in claves:
                claves.append(clave)
    if not claves:
        if not getattr(settings, 'MFA_CLAVE_DERIVADA_DESARROLLO', False):
            raise ImproperlyConfigured('Defina DB_CLAVE_CIFRADO o MFA_CLAVE_CIFRADO en producción.')
        derivada = base64.urlsafe_b64encode(
            hashlib.sha256(('db-enc|' + settings.SECRET_KEY).encode('utf-8')).digest()
        )
        claves = [derivada]
    return MultiFernet([Fernet(c.encode('utf-8') if isinstance(c, str) else c) for c in claves])


def cifrar_texto(valor):
    """Cifra una cadena con MultiFernet. Si ya está cifrada o vacía, la devuelve sin doble cifrar."""
    if valor is None or valor == '':
        return valor
    texto = str(valor)
    if texto.startswith(PREFIJO_CIFRADO):
        return texto
    token = _obtener_fernet().encrypt(texto.encode('utf-8')).decode('ascii')
    return PREFIJO_CIFRADO + token


def descifrar_texto(valor):
    """Descifra un valor con prefijo ``enc:f1:``. Si viene en texto plano heredado, lo devuelve igual."""
    if valor is None or valor == '':
        return valor
    texto = str(valor)
    if not texto.startswith(PREFIJO_CIFRADO):
        return texto
    try:
        return _obtener_fernet().decrypt(texto[len(PREFIJO_CIFRADO):].encode('ascii')).decode('utf-8')
    except InvalidToken as exc:
        raise ImproperlyConfigured(
            'No se pudo descifrar un campo protegido de la base de datos: revise DB_CLAVE_CIFRADO / MFA_CLAVE_CIFRADO.'
        ) from exc


def esta_cifrado(valor):
    """Indica si una cadena ya cuenta con el prefijo autenticado enc:f1:."""
    return isinstance(valor, str) and valor.startswith(PREFIJO_CIFRADO)


def indice_ciego(valor, contexto='correo'):
    """Calcula un índice ciego HMAC-SHA256 determinístico para búsquedas e integridad sin exponer el valor."""
    if not valor:
        return ''
    normalizado = str(valor).strip().lower()
    llave = hashlib.sha256(('blind-index|' + contexto + '|' + settings.SECRET_KEY).encode('utf-8')).digest()
    return hmac.new(llave, normalizado.encode('utf-8'), hashlib.sha256).hexdigest()


class CampoTextoCifrado(models.TextField):
    """Campo Django que cifra automáticamente al escribir en BD y descifra al leer.

    Conserva opcionalmente ``max_length_logico`` para validación en formularios sin truncar
    el texto cifrado (que es más largo que el texto plano).
    """

    def __init__(self, *args, max_length_logico=None, **kwargs):
        self.max_length_logico = max_length_logico
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        """Serializa el campo y su longitud lógica para las migraciones de Django."""
        name, path, args, kwargs = super().deconstruct()
        if self.max_length_logico is not None:
            kwargs['max_length_logico'] = self.max_length_logico
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        """Renderiza el campo en formularios como CharField respetando max_length_logico."""
        from django import forms
        defaults = {'form_class': forms.CharField}
        if self.max_length_logico is not None:
            defaults['max_length'] = self.max_length_logico
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def from_db_value(self, value, expression, connection):
        """Descifra automáticamente el valor al leerlo desde la base de datos."""
        return descifrar_texto(value)

    def to_python(self, value):
        """Normaliza y descifra el valor en memoria al deserializar formularios o modelos."""
        if value is None:
            return value
        return descifrar_texto(value)

    def get_prep_value(self, value):
        """Cifra automáticamente el valor antes de enviarlo a la base de datos."""
        value = super().get_prep_value(value)
        if value is None or value == '':
            return value
        return cifrar_texto(value)
