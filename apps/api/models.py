"""Modelos del API Gateway: llaves de acceso (hash SHA-256) y bitácora inmutable de peticiones."""
import hashlib
import hmac
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.rls import contexto_rls_sistema, filtrar_por_rls


class PermisoApi(models.TextChoices):
    """Niveles de permiso asignables a una API Key (principio de mínimo privilegio)."""
    LECTURA = 'LECTURA', 'Solo lectura (GET)'
    LECTURA_ESCRITURA = 'LECTURA_ESCRITURA', 'Lectura y escritura (GET/POST)'


def _hash_clave(clave_plana):
    """Calcula el resumen SHA-256 hexadecimal de una API Key para almacenamiento seguro."""
    return hashlib.sha256(clave_plana.encode('utf-8')).hexdigest()


class ApiKey(models.Model):
    """Llave de acceso al API Gateway. Solo se almacena su hash SHA-256 (nunca en texto plano)."""
    nombre = models.CharField('nombre', max_length=120)
    prefijo = models.CharField('prefijo', max_length=16, db_index=True)
    clave_hash = models.CharField('hash SHA-256', max_length=64, unique=True)
    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_keys',
    )
    permisos = models.CharField(
        'permisos', max_length=20, choices=PermisoApi.choices, default=PermisoApi.LECTURA_ESCRITURA,
    )
    limite_por_minuto = models.PositiveIntegerField('límite por minuto', default=60)
    activa = models.BooleanField('activa', default=True)
    ultimo_uso = models.DateTimeField('último uso', null=True, blank=True)
    creada_en = models.DateTimeField('creada en', auto_now_add=True)

    class Meta:
        db_table = 'api_clave'
        ordering = ['-creada_en']

    def __str__(self):
        return f'{self.nombre} ({self.prefijo}...)'

    @classmethod
    def generar(cls, nombre, propietario, permisos=PermisoApi.LECTURA_ESCRITURA, limite_por_minuto=60):
        """Genera una API Key CSPRNG, almacena únicamente su hash SHA-256 y devuelve (instancia, clave_plana)."""
        clave_plana = f'ecp_{secrets.token_urlsafe(32)}'
        instancia = cls.objects.create(
            nombre=nombre[:120],
            prefijo=clave_plana[:12],
            clave_hash=_hash_clave(clave_plana),
            propietario=propietario,
            permisos=permisos,
            limite_por_minuto=limite_por_minuto,
        )
        return instancia, clave_plana

    @classmethod
    def validar(cls, clave_plana):
        """Valida una API Key usando comparación en tiempo constante (hmac.compare_digest) y actualiza ultimo_uso."""
        if not clave_plana or not isinstance(clave_plana, str) or len(clave_plana) < 20:
            return None
        prefijo = clave_plana[:12]
        candidato_hash = _hash_clave(clave_plana)
        with contexto_rls_sistema():
            for llave in cls.objects.select_related('propietario').filter(prefijo=prefijo, activa=True):
                if hmac.compare_digest(llave.clave_hash, candidato_hash) and llave.propietario.is_active:
                    cls.objects.filter(pk=llave.pk).update(ultimo_uso=timezone.now())
                    return llave
        return None

    def permite_escritura(self):
        """Devuelve True si la API Key autoriza operaciones de escritura (POST)."""
        return self.permisos == PermisoApi.LECTURA_ESCRITURA

    @classmethod
    def para_usuario_rls(cls, usuario):
        """Aplica aislamiento Row-Level Security sobre las API Keys visibles para el usuario."""
        return filtrar_por_rls(cls.objects.all(), usuario, campo_usuario='propietario')


class RegistroGateway(models.Model):
    """Bitácora inmutable del API Gateway (trazabilidad de GET/POST y bloqueos de seguridad).

    No almacena IPs en texto plano (usa huella HMAC rotativa, RN-08) ni contraseñas/llaves.
    """
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    metodo = models.CharField(max_length=10)
    ruta = models.CharField(max_length=255)
    codigo_estado = models.PositiveSmallIntegerField()
    duracion_ms = models.PositiveIntegerField(default=0)
    api_key = models.ForeignKey(ApiKey, null=True, blank=True, on_delete=models.SET_NULL, related_name='registros')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    huella_cliente = models.CharField(max_length=32, blank=True, default='')
    bloqueado = models.BooleanField(default=False, db_index=True)
    motivo_bloqueo = models.CharField(max_length=60, blank=True, default='')
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'api_gateway_log'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['fecha_hora', 'bloqueado'], name='ix_gw_fecha_bloq'),
        ]

    def __str__(self):
        return f'{self.metodo} {self.ruta} -> {self.codigo_estado}'

    def save(self, *args, **kwargs):
        """Impide la modificación de registros ya persistidos para preservar la cadena de auditoría."""
        if self.pk:
            raise ValueError('Los registros del API Gateway son inmutables.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Impide el borrado de registros de auditoría del API Gateway."""
        raise ValueError('Los registros del API Gateway no se pueden borrar.')
