"""Adaptador de verificación en dos pasos: cifra los secretos TOTP en la base de datos (OWASP A04)."""
import base64
import hashlib

from allauth.mfa.adapter import DefaultMFAAdapter
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

PREFIJO = 'f1:'


def _fernet():
    claves = [c for c in getattr(settings, 'MFA_CLAVES_CIFRADO', []) if c]
    if not claves:
        if not getattr(settings, 'MFA_CLAVE_DERIVADA_DESARROLLO', False):
            raise ImproperlyConfigured('Defina MFA_CLAVE_CIFRADO (clave Fernet) en producción.')
        derivada = base64.urlsafe_b64encode(hashlib.sha256(('mfa|' + settings.SECRET_KEY).encode()).digest())
        claves = [derivada]
    return MultiFernet([Fernet(c) for c in claves])  # la primera cifra; todas descifran (rotación)


class MFAAdapter(DefaultMFAAdapter):
    def encrypt(self, text):
        return PREFIJO + _fernet().encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        if not encrypted_text.startswith(PREFIJO):
            return encrypted_text
        try:
            return _fernet().decrypt(encrypted_text[len(PREFIJO):].encode()).decode()
        except InvalidToken as e:
            raise ImproperlyConfigured('No se pudo descifrar un secreto TOTP: revise MFA_CLAVE_CIFRADO.') from e

    def can_delete_authenticator(self, authenticator):
        """Un administrador no puede apagar su verificación en dos pasos (sí regenerar códigos)."""
        if authenticator.user.es_personal and authenticator.type == authenticator.Type.TOTP:
            return False
        return super().can_delete_authenticator(authenticator)

    def get_totp_label(self, user):
        return user.correo
