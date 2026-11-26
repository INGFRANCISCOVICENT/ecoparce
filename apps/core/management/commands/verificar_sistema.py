"""Diagnóstico integral de EcoParce: cifrado, RLS, correo SMTP, Google OAuth y APIs remotas."""
import smtplib
import ssl
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from apps.core.cifrado import esta_cifrado
from apps.core.context_processors import google_configurado
from apps.core.rls import POLITICAS_RLS_POSTGRES


class Command(BaseCommand):
    help = 'Verifica cifrado de cuentas, RLS, configuración de correo/Google y conexiones remotas.'

    def add_arguments(self, parser):
        parser.add_argument('--probar-remoto', action='store_true', help='Prueba conectividad HTTPS real a APIs remotas.')
        parser.add_argument('--probar-smtp', action='store_true', help='Prueba conexión y login SMTP real (Gmail/Resend).')

    def handle(self, *args, **options):
        self.stdout.write('=== Diagnóstico de seguridad y conectividad de EcoParce ===')

        # 1. Base de datos y cifrado
        with connection.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM usuario')
            total_u = cur.fetchone()[0]
            cur.execute('SELECT nombre, correo_hash FROM usuario')
            filas = cur.fetchall()
        cifrados = sum(1 for nombre, _ in filas if not nombre or esta_cifrado(nombre))
        con_hash = sum(1 for _, h in filas if h and len(h) == 64)
        self.stdout.write(
            f'[BD] Motor={connection.vendor} | Usuarios={total_u} | '
            f'Nombres cifrados={cifrados}/{total_u} | Huella correo_hash={con_hash}/{total_u}'
        )

        # 2. RLS
        if connection.vendor == 'postgresql':
            self.stdout.write(f'[RLS] PostgreSQL detectado ({len(POLITICAS_RLS_POSTGRES)} políticas declarativas listas).')
        else:
            self.stdout.write(
                f'[RLS] Motor {connection.vendor}: capa RLS de aplicación activa; '
                f'script PostgreSQL en docs/rls_postgresql.sql ({len(POLITICAS_RLS_POSTGRES)} políticas).'
            )

        # 3. Google OAuth y Correo / Códigos
        self.stdout.write(f'[Google OAuth] Configurado={google_configurado()}')
        smtp_host = getattr(settings, 'EMAIL_HOST', '')
        self.stdout.write(
            f'[Correo] Backend={settings.EMAIL_BACKEND} | SMTP_HOST={smtp_host or "(no configurado -> consola)"} | '
            f'CodigoRegistro={settings.ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED} | '
            f'CodigoReset={settings.ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED}'
        )

        if options['probar_smtp']:
            if not smtp_host:
                self.stdout.write(self.style.WARNING('[SMTP] No hay SMTP_HOST configurado en .env; omitiendo prueba real.'))
            else:
                try:
                    ctx = ssl.create_default_context()
                    if settings.EMAIL_USE_SSL:
                        srv = smtplib.SMTP_SSL(smtp_host, settings.EMAIL_PORT, timeout=10, context=ctx)
                    else:
                        srv = smtplib.SMTP(smtp_host, settings.EMAIL_PORT, timeout=10)
                        if settings.EMAIL_USE_TLS:
                            srv.starttls(context=ctx)
                    with srv:
                        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                            srv.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    self.stdout.write(self.style.SUCCESS(f'[SMTP] Conexión y autenticación OK con {smtp_host}:{settings.EMAIL_PORT}'))
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f'[SMTP] Error conectando con {smtp_host}: {exc}'))

        if options['probar_remoto']:
            from apps.contenidos.management.commands.sincronizar_puntos_sda import URL_SDA
            urls = [
                ('Open Food Facts', 'https://world.openfoodfacts.org/api/v2/product/7702004003508.json?fields=product_name,brands'),
                ('SDA Bogotá (Puntos Posconsumo)', URL_SDA.format(limite=1, offset=0)),
            ]
            for nombre, url in urls:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={'User-Agent': 'EcoParce-Diagnostico/2.0', 'Accept': 'application/json'},
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310: URLs fijas HTTPS
                        self.stdout.write(self.style.SUCCESS(f'[Remoto] {nombre}: HTTP {resp.status} OK'))
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    self.stdout.write(self.style.WARNING(f'[Remoto] {nombre}: no accesible ({exc})'))
