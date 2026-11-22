"""
Carga las guías, residuos y preguntas iniciales de EcoParce ya revisadas y publicadas.

    python manage.py cargar_contenido_inicial --autor danixa@ecoparce.com.co --revisor darien@ecoparce.com.co
    python manage.py cargar_contenido_inicial --autor ... --revisor ... --demo   # agrega puntos y un QR de ejemplo

Es idempotente: se puede ejecutar varias veces sin duplicar datos.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.contenidos import datos_iniciales as D
from apps.contenidos.models import Contenedor, EstadoContenido, Guia, PuntoEntrega, Residuo
from apps.cuentas.models import Usuario
from apps.trivia.models import OpcionTrivia, PreguntaTrivia


class Command(BaseCommand):
    help = 'Carga el contenido inicial verificado (Resolución 2184 de 2019 y normas posconsumo).'

    def add_arguments(self, parser):
        parser.add_argument('--autor', required=True, help='Correo del administrador que figura como autor.')
        parser.add_argument('--revisor', required=True, help='Correo de otro administrador que figura como revisor (RN-03).')
        parser.add_argument('--demo', action='store_true', help='Agrega puntos de entrega e institución de ejemplo.')

    def _usuario(self, correo):
        try:
            return Usuario.objects.get(correo=correo.lower(), is_active=True)
        except Usuario.DoesNotExist:
            raise CommandError(f'No existe un administrador activo con el correo {correo}. Créalo primero con createsuperuser.')

    @transaction.atomic
    def handle(self, *args, **o):
        autor, revisor = self._usuario(o['autor']), self._usuario(o['revisor'])
        if autor == revisor:
            raise CommandError('El autor y el revisor deben ser personas distintas (RN-03).')
        ahora = timezone.now()
        contenedores = {c.codigo: c for c in Contenedor.objects.all()}
        if len(contenedores) < 4:
            raise CommandError('Faltan los contenedores. Ejecute primero: python manage.py migrate')
        publicado = {'estado': EstadoContenido.PUBLICADO, 'autor': autor, 'revisor': revisor}

        guias = {}
        for slug, titulo, tipo, cont, resumen, cuerpo, fuente in D.GUIAS:
            g, _ = Guia.objects.update_or_create(slug=slug, defaults={
                'titulo': titulo, 'tipo': tipo, 'contenedor': contenedores.get(cont), 'resumen': resumen,
                'cuerpo': cuerpo, 'fuente_oficial': fuente, 'publicado_en': ahora, **publicado})
            guias[slug] = g

        for nombre, sinonimos, cont, slug, prep in D.RESIDUOS + D.RESIDUOS_POSCONSUMO_EXTRA:
            Residuo.objects.update_or_create(nombre=nombre, defaults={
                'sinonimos': sinonimos, 'contenedor': contenedores[cont], 'guia': guias.get(slug),
                'preparacion': prep, 'es_especial': cont == Contenedor.POSCONSUMO, **publicado})

        nuevas = 0
        bloques = [
            ('GENERAL', D.PREGUNTAS),
            ('BOLSAS', D.PREGUNTAS_BOLSAS),
            ('MITOS', D.PREGUNTAS_MITOS),
        ]
        for categoria, lista in bloques:
            for enunciado, explicacion, dificultad, opciones in lista:
                p, creada = PreguntaTrivia.objects.get_or_create(enunciado=enunciado, defaults={
                    'explicacion': explicacion, 'dificultad': dificultad, 'categoria': categoria, 'autor': autor})
                if creada:
                    for i, (texto, correcta) in enumerate(opciones, start=1):
                        OpcionTrivia.objects.create(pregunta=p, texto=texto, es_correcta=correcta, orden=i)
                    p.activa = p.validar()
                    p.save(update_fields=['activa'])
                    nuevas += 1
                elif p.categoria != categoria:
                    p.categoria = categoria
                    p.save(update_fields=['categoria'])

        if o['demo']:
            from apps.qr.models import Institucion
            for nombre, direccion, localidad, horario, residuos in D.PUNTOS_DEMO:
                punto, _ = PuntoEntrega.objects.update_or_create(nombre=nombre, defaults={
                    'direccion': direccion, 'localidad': localidad, 'horario': horario, 'activo': True})
                punto.residuos.set(Residuo.objects.filter(nombre__in=residuos))
            Institucion.objects.get_or_create(nombre='Conjunto residencial (ejemplo)', defaults={'tipo': 'CONJUNTO'})

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {len(D.GUIAS)} guías y {len(D.RESIDUOS) + len(D.RESIDUOS_POSCONSUMO_EXTRA)} residuos publicados, {nuevas} preguntas nuevas'
            + (f', {len(D.PUNTOS_DEMO)} puntos de ejemplo.' if o['demo'] else '.')))
