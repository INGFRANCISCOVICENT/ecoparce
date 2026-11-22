"""Los administradores que ya existían fueron creados por el administrador del sistema:
se registra su correo como verificado para que puedan seguir entrando con la verificación obligatoria."""
from django.db import migrations


def marcar(apps, schema_editor):
    Usuario = apps.get_model('cuentas', 'Usuario')
    EmailAddress = apps.get_model('account', 'EmailAddress')
    for u in Usuario.objects.filter(rol__in=['CONTENIDO', 'SISTEMA']):
        EmailAddress.objects.update_or_create(user_id=u.pk, email=u.correo, defaults={'verified': True, 'primary': True})


class Migration(migrations.Migration):
    dependencies = [('cuentas', '0002_cuentas_google_y_visitantes'), ('account', '0001_initial')]
    operations = [migrations.RunPython(marcar, migrations.RunPython.noop)]
