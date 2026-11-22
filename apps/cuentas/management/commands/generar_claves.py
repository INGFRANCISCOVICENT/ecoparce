"""Genera claves nuevas para el archivo .env de producción (no las guarda en ningún lado).

    python manage.py generar_claves
"""
import secrets

from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Genera DJANGO_SECRET_KEY y MFA_CLAVE_CIFRADO aleatorias para el .env.'

    def handle(self, *args, **o):
        self.stdout.write(f'DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}')
        self.stdout.write(f'MFA_CLAVE_CIFRADO={Fernet.generate_key().decode()}')
        self.stderr.write('Cópielas al .env del servidor (chmod 600). No las suba a Git ni las comparta por chat.')
