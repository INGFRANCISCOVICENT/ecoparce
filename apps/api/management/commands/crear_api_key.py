"""Genera una API Key para consumir el API Gateway de EcoParce (GET/POST)."""
from django.core.management.base import BaseCommand, CommandError

from apps.api.models import ApiKey, PermisoApi
from apps.cuentas.models import Usuario


class Command(BaseCommand):
    help = 'Crea una API Key con hash SHA-256 para un usuario existente.'

    def add_arguments(self, parser):
        parser.add_argument('--correo', required=True, help='Correo del usuario propietario de la llave.')
        parser.add_argument('--nombre', default='Cliente API', help='Nombre descriptivo de la llave.')
        parser.add_argument(
            '--solo-lectura',
            action='store_true',
            help='Restringe la llave únicamente a peticiones GET.',
        )
        parser.add_argument('--limite', type=int, default=60, help='Peticiones máximas por minuto.')

    def handle(self, *args, **options):
        usuario = Usuario.objects.filter(correo=options['correo'].strip().lower(), is_active=True).first()
        if not usuario:
            raise CommandError(f"No existe un usuario activo con el correo {options['correo']}.")
        permisos = PermisoApi.LECTURA if options['solo_lectura'] else PermisoApi.LECTURA_ESCRITURA
        llave, clave_plana = ApiKey.generar(
            nombre=options['nombre'],
            propietario=usuario,
            permisos=permisos,
            limite_por_minuto=max(1, options['limite']),
        )
        self.stdout.write(self.style.SUCCESS(f'API Key creada: {llave.nombre} ({llave.permisos})'))
        self.stdout.write(f'GUARDA ESTA CLAVE AHORA (no se volverá a mostrar): {clave_plana}')
