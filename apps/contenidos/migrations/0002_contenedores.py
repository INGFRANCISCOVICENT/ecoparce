"""RN-04: el código de colores de la Resolución 2184 de 2019 es dato semilla, no se edita desde el panel."""
from django.db import migrations

CONTENEDORES = [
    (1, 'BLANCA', 'Bolsa blanca', '#FFFFFF', 'Aprovechables: plástico, vidrio, metales, multicapa, papel y cartón limpios y secos'),
    (2, 'NEGRA', 'Bolsa negra', '#1A1A1A', 'No aprovechables: papel higiénico, servilletas, papeles y cartones con comida'),
    (3, 'VERDE', 'Bolsa verde', '#2E7D32', 'Orgánicos aprovechables: restos de comida, cáscaras y desechos agrícolas'),
    (4, 'POSCONSUMO', 'Punto posconsumo', '#C81E1E', 'Residuos especiales: pilas, aparatos eléctricos, medicamentos, bombillos y aceite usado'),
]


def crear(apps, schema_editor):
    Contenedor = apps.get_model('contenidos', 'Contenedor')
    for pk, codigo, nombre, color, desc in CONTENEDORES:
        Contenedor.objects.update_or_create(pk=pk, defaults={'codigo': codigo, 'nombre': nombre, 'color_hex': color, 'descripcion': desc})


def borrar(apps, schema_editor):
    apps.get_model('contenidos', 'Contenedor').objects.filter(pk__in=[c[0] for c in CONTENEDORES]).delete()


class Migration(migrations.Migration):
    dependencies = [('contenidos', '0001_initial')]
    operations = [migrations.RunPython(crear, borrar)]
