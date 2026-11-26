"""Aplica políticas de Row-Level Security (RLS) en PostgreSQL y exporta el script SQL."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from apps.core.rls import aplicar_politicas_postgresql, generar_sql_rls


class Command(BaseCommand):
    help = 'Aplica Row-Level Security (RLS) en PostgreSQL y exporta docs/rls_postgresql.sql.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exportar-sql',
            action='store_true',
            help='Exporta el script SQL idempotente a docs/rls_postgresql.sql.',
        )

    def handle(self, *args, **options):
        sql = generar_sql_rls()
        if options['exportar_sql']:
            destino = Path(settings.BASE_DIR) / 'docs' / 'rls_postgresql.sql'
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(sql, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'Script RLS exportado en {destino}'))

        aplicadas = aplicar_politicas_postgresql()
        if aplicadas is None:
            self.stdout.write(
                self.style.WARNING(
                    f'Motor actual ({connection.vendor}): RLS nativo aplica en PostgreSQL (Render/Supabase). '
                    'En este motor sigue activa la capa RLS de aplicación (RLSContextMiddleware + filtrar_por_rls).'
                )
            )
            return
        self.stdout.write(
            self.style.SUCCESS(f'RLS aplicado en PostgreSQL sobre {len(aplicadas)} tablas: {", ".join(aplicadas)}')
        )
