"""Cifrado autenticado de extremo a extremo (E2E) con AES-256-GCM y derivación HKDF-SHA256.

Proporciona confidencialidad e integridad criptográfica (AEAD, NIST SP 800-38D):
- Llave de 256 bits derivada mediante HKDF-SHA256 con contexto separado de SECRET_KEY.
- Nonce aleatorio de 96 bits (12 bytes CSPRNG) único por cada mensaje cifrado.
- Datos Asociados Autenticados (AAD) vinculados al propietario/contexto para impedir
  trasplante de mensajes cifrados entre usuarios distintos.
"""
import base64
import hashlib
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings


def _derivar_clave_aes256():
    """Deriva una llave simétrica de 256 bits mediante HKDF-SHA256 separada de SECRET_KEY."""
    base = ''
    for nombre in ('DB_CLAVES_CIFRADO', 'MFA_CLAVES_CIFRADO'):
        claves = getattr(settings, nombre, None) or []
        if claves:
            base = str(claves[0])
            break
    if not base:
        base = settings.SECRET_KEY
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'ecoparce-e2e-aes256gcm-v1',
        info=b'ecoparce-envelope-key',
    )
    return hkdf.derive(base.encode('utf-8'))


def cifrar_sobre_e2e(datos, aad=''):
    """Cifra un diccionario JSON en un sobre autenticado AES-256-GCM vinculado al AAD."""
    llave = _derivar_clave_aes256()
    nonce = os.urandom(12)
    aad_bytes = str(aad or '').encode('utf-8')
    plano = json.dumps(datos, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    ct = AESGCM(llave).encrypt(nonce, plano, aad_bytes)
    return {
        'alg': 'AES-256-GCM',
        'nonce': base64.urlsafe_b64encode(nonce).decode('ascii'),
        'ciphertext': base64.urlsafe_b64encode(ct).decode('ascii'),
        'aad_sha256': hashlib.sha256(aad_bytes).hexdigest()[:16],
    }


def descifrar_sobre_e2e(sobre, aad=''):
    """Verifica la etiqueta GCM y el AAD, y devuelve el diccionario JSON original."""
    if not isinstance(sobre, dict) or sobre.get('alg') != 'AES-256-GCM':
        raise ValueError('Sobre E2E inválido o algoritmo no soportado.')
    try:
        nonce = base64.urlsafe_b64decode(sobre['nonce'].encode('ascii'))
        ct = base64.urlsafe_b64decode(sobre['ciphertext'].encode('ascii'))
    except Exception as exc:
        raise ValueError('Codificación base64 inválida en sobre E2E.') from exc
    if len(nonce) != 12:
        raise ValueError('Longitud de nonce AES-GCM inválida.')
    aad_bytes = str(aad or '').encode('utf-8')
    try:
        plano = AESGCM(_derivar_clave_aes256()).decrypt(nonce, ct, aad_bytes)
    except InvalidTag as exc:
        raise ValueError('Falló la verificación de integridad AES-256-GCM (datos alterados o AAD incorrecto).') from exc
    return json.loads(plano.decode('utf-8'))
