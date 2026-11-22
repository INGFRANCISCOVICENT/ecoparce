from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.auditoria.models import Accion, RegistroAuditoria


class Busqueda(models.Model):
    """Registro anónimo de cada búsqueda (RF-10, RN-08): sin IP ni datos personales."""
    termino = models.CharField(max_length=100)
    residuo = models.ForeignKey('contenidos.Residuo', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    encontrado = models.BooleanField()
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'busqueda'
        ordering = ['-fecha_hora']
        indexes = [models.Index(fields=['fecha_hora'], name='ix_busqueda_fecha'),
                   models.Index(fields=['termino'], name='ix_busqueda_termino')]

    def __str__(self):
        return self.termino


class EstadoSugerencia(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    ATENDIDA = 'ATENDIDA', 'Atendida'
    DESCARTADA = 'DESCARTADA', 'Descartada'


class Sugerencia(models.Model):
    termino = models.CharField('residuo', max_length=100)
    comentario = models.CharField(max_length=300, blank=True)
    estado = models.CharField(max_length=12, choices=EstadoSugerencia.choices, default=EstadoSugerencia.PENDIENTE)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='sugerencias')
    atendida_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    atendida_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sugerencia'
        ordering = ['-fecha_hora']
        indexes = [models.Index(fields=['estado'], name='ix_sugerencia_estado')]
        constraints = [models.CheckConstraint(condition=models.Q(estado__in=['PENDIENTE', 'ATENDIDA', 'DESCARTADA']),
                                              name='ck_sugerencia_estado')]

    def __str__(self):
        return self.termino

    def atender(self, admin, estado=EstadoSugerencia.ATENDIDA):
        self.estado = estado
        self.atendida_por = admin
        self.atendida_en = timezone.now()
        self.save()
        RegistroAuditoria.registrar(admin, Accion.ATENDER, self, f'{self.termino}: {self.get_estado_display()}')
