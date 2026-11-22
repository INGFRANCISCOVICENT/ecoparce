from django.conf import settings
from django.db import models


class Accion(models.TextChoices):
    INGRESO = 'INGRESO', 'Ingreso al panel'
    CREAR = 'CREAR', 'Crear'
    EDITAR = 'EDITAR', 'Editar'
    ENVIAR_REVISION = 'ENVIAR_REVISION', 'Enviar a revisión'
    PUBLICAR = 'PUBLICAR', 'Publicar'
    DEVOLVER = 'DEVOLVER', 'Devolver con observaciones'
    RETIRAR = 'RETIRAR', 'Retirar'
    REABRIR = 'REABRIR', 'Reabrir para corregir'
    ELIMINAR = 'ELIMINAR', 'Eliminar'
    ACTIVAR = 'ACTIVAR', 'Activar'
    DESACTIVAR = 'DESACTIVAR', 'Desactivar'
    ATENDER = 'ATENDER', 'Atender'


class RegistroAuditoria(models.Model):
    """Registro inmutable de acciones de los administradores (RNF-02)."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    accion = models.CharField(max_length=40, choices=Accion.choices)
    entidad = models.CharField(max_length=40)
    entidad_id = models.BigIntegerField(null=True)
    detalle = models.CharField(max_length=500, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'registro_auditoria'
        ordering = ['-fecha_hora']
        indexes = [models.Index(fields=['fecha_hora'], name='ix_auditoria_fecha'),
                   models.Index(fields=['entidad', 'entidad_id'], name='ix_auditoria_entidad')]

    def __str__(self):
        return f'{self.fecha_hora:%Y-%m-%d %H:%M} {self.accion} {self.entidad}#{self.entidad_id}'

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('Los registros de auditoría no se pueden modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Los registros de auditoría no se pueden borrar.')

    @classmethod
    def registrar(cls, usuario, accion, objeto=None, detalle='', entidad=None):
        return cls.objects.create(
            usuario=usuario if getattr(usuario, 'pk', None) else None,
            accion=accion,
            entidad=entidad or (objeto._meta.db_table if objeto is not None else ''),
            entidad_id=getattr(objeto, 'pk', None),
            detalle=str(detalle)[:500],
        )
