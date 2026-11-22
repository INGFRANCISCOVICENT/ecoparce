from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.auditoria.models import Accion, RegistroAuditoria
from apps.core.texto import normalizar


class EstadoContenido(models.TextChoices):
    BORRADOR = 'BORRADOR', 'Borrador'
    EN_REVISION = 'EN_REVISION', 'En revisión'
    PUBLICADO = 'PUBLICADO', 'Publicado'
    RETIRADO = 'RETIRADO', 'Retirado'


ESTADOS = [e.value for e in EstadoContenido]


class Contenedor(models.Model):
    """Código de colores de la Resolución 2184 de 2019 y punto posconsumo (RN-04, RN-05)."""
    BLANCA, NEGRA, VERDE, POSCONSUMO = 'BLANCA', 'NEGRA', 'VERDE', 'POSCONSUMO'

    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=60)
    color_hex = models.CharField(max_length=7)
    descripcion = models.CharField(max_length=300)

    class Meta:
        db_table = 'contenedor'
        ordering = ['id']

    def __str__(self):
        return self.nombre

    @property
    def es_bolsa(self):
        return self.codigo != self.POSCONSUMO


class ContenidoRevisable(models.Model):
    """Comportamiento común de guías y residuos: flujo de revisión (RN-01 a RN-03)."""
    estado = models.CharField(max_length=12, choices=EstadoContenido.choices, default=EstadoContenido.BORRADOR)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='+')
    revisor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.RESTRICT, related_name='+')
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    # --- transiciones del diagrama de estados ---
    def _auditar(self, usuario, accion, detalle=''):
        RegistroAuditoria.registrar(usuario, accion, self, detalle or str(self))

    def enviar_a_revision(self, usuario):
        if self.estado != EstadoContenido.BORRADOR:
            raise ValidationError('Solo un borrador se puede enviar a revisión.')
        fuente = getattr(self, 'fuente_oficial', None)
        if fuente is not None and not fuente.strip():
            raise ValidationError('Registre la fuente oficial antes de enviar a revisión (RN-02).')
        self.estado = EstadoContenido.EN_REVISION
        self.save()
        self._auditar(usuario, Accion.ENVIAR_REVISION)

    def publicar(self, revisor):
        if self.estado != EstadoContenido.EN_REVISION:
            raise ValidationError('Solo se publica contenido que está en revisión.')
        if not revisor.puede_publicar(self):
            raise PermissionDenied('El revisor debe ser un administrador distinto del autor (RN-03).')
        self.estado = EstadoContenido.PUBLICADO
        self.revisor = revisor
        if hasattr(self, 'publicado_en'):
            self.publicado_en = timezone.now()
        self.save()
        self._auditar(revisor, Accion.PUBLICAR)

    def devolver(self, revisor, observaciones):
        if self.estado != EstadoContenido.EN_REVISION:
            raise ValidationError('Solo se devuelve contenido que está en revisión.')
        if not revisor.puede_publicar(self):
            raise PermissionDenied('El revisor debe ser un administrador distinto del autor (RN-03).')
        if not observaciones.strip():
            raise ValidationError('Escriba las observaciones para el autor.')
        self.estado = EstadoContenido.BORRADOR
        self.save()
        self._auditar(revisor, Accion.DEVOLVER, f'{self}: {observaciones}')

    def retirar(self, usuario):
        if self.estado != EstadoContenido.PUBLICADO:
            raise ValidationError('Solo se retira contenido publicado.')
        self.estado = EstadoContenido.RETIRADO
        self.save()
        self._auditar(usuario, Accion.RETIRAR)

    def reabrir(self, usuario):
        if self.estado != EstadoContenido.RETIRADO:
            raise ValidationError('Solo se reabre contenido retirado.')
        self.estado = EstadoContenido.BORRADOR
        self.revisor = None
        self.save()
        self._auditar(usuario, Accion.REABRIR)

    @property
    def publicado(self):
        return self.estado == EstadoContenido.PUBLICADO


class GuiaPublicadaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(estado=EstadoContenido.PUBLICADO)


class TipoGuia(models.TextChoices):
    SEPARACION = 'SEPARACION', 'Separación'
    MANEJO = 'MANEJO', 'Manejo de basuras'
    ESPECIAL = 'ESPECIAL', 'Residuos especiales'


class Guia(ContenidoRevisable):
    titulo = models.CharField('título', max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    tipo = models.CharField(max_length=12, choices=TipoGuia.choices, default=TipoGuia.SEPARACION)
    resumen = models.CharField(max_length=300)
    cuerpo = models.TextField(help_text='Use líneas que empiecen con «+» para lo que sí va y con «-» para lo que no va.')
    contenedor = models.ForeignKey(Contenedor, null=True, blank=True, on_delete=models.SET_NULL, related_name='guias')
    fuente_oficial = models.CharField('fuente oficial', max_length=300, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    publicado_en = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()
    publicadas = GuiaPublicadaManager()

    class Meta:
        db_table = 'guia'
        ordering = ['tipo', 'titulo']
        indexes = [models.Index(fields=['estado'], name='ix_guia_estado')]
        constraints = [
            models.CheckConstraint(condition=models.Q(tipo__in=['SEPARACION', 'MANEJO', 'ESPECIAL']), name='ck_guia_tipo'),
            models.CheckConstraint(condition=models.Q(estado__in=ESTADOS), name='ck_guia_estado'),
            models.CheckConstraint(condition=models.Q(revisor__isnull=True) | ~models.Q(revisor=models.F('autor')),
                                   name='ck_guia_revisor'),
        ]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titulo)[:150] or 'guia'
            slug, n = base, 2
            while Guia.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f'{base}-{n}', n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('contenidos:guia', args=[self.slug])

    url_publica = get_absolute_url

    def lineas(self, signo):
        return [ln[1:].strip() for ln in self.cuerpo.splitlines() if ln.strip().startswith(signo) and ln.strip()[1:].strip()]

    @property
    def que_va(self):
        return self.lineas('+')

    @property
    def que_no_va(self):
        return self.lineas('-')

    @property
    def parrafos(self):
        return [ln.strip() for ln in self.cuerpo.splitlines() if ln.strip() and ln.strip()[0] not in '+-']


class Residuo(ContenidoRevisable):
    nombre = models.CharField(max_length=100, unique=True)
    sinonimos = models.CharField(max_length=300, blank=True, help_text='Otros nombres separados por coma.')
    preparacion = models.CharField('preparación', max_length=300, blank=True,
                                   help_text='Pasos separados por punto y coma, por ejemplo: vacíala; enjuágala; déjala seca.')
    contenedor = models.ForeignKey(Contenedor, on_delete=models.RESTRICT, related_name='residuos')
    guia = models.ForeignKey(Guia, verbose_name='guía', null=True, blank=True, on_delete=models.SET_NULL, related_name='residuos')
    es_especial = models.BooleanField('residuo especial', default=False)

    class Meta:
        db_table = 'residuo'
        ordering = ['nombre']
        indexes = [models.Index(fields=['estado'], name='ix_residuo_estado')]
        constraints = [
            models.CheckConstraint(condition=models.Q(estado__in=ESTADOS), name='ck_residuo_estado'),
            models.CheckConstraint(condition=models.Q(revisor__isnull=True) | ~models.Q(revisor=models.F('autor')),
                                   name='ck_residuo_revisor'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def pasos(self):
        return [p.strip() for p in self.preparacion.split(';') if p.strip()]

    def terminos(self):
        return [normalizar(self.nombre)] + [normalizar(s) for s in self.sinonimos.split(',') if s.strip()]

    def coincide_con(self, termino):
        """Compara el término normalizado con nombre y sinónimos normalizados."""
        t = normalizar(termino)
        if not t:
            return False
        return any(t == x or t in x or (len(x) > 3 and x in t) for x in self.terminos())

    def puntuacion(self, termino):
        t = normalizar(termino)
        ts = self.terminos()
        if t == ts[0]:
            return 0
        if t in ts:
            return 1
        return 2


class FuentePunto(models.TextChoices):
    SDA = 'SDA', 'Secretaría Distrital de Ambiente (Visor Geográfico Ambiental)'
    MANUAL = 'MANUAL', 'Registrado por EcoParce'


class PuntoEntrega(models.Model):
    nombre = models.CharField(max_length=160)
    direccion = models.CharField('dirección', max_length=160)
    localidad = models.CharField(max_length=60)
    barrio = models.CharField('sector o barrio', max_length=80, blank=True)
    horario = models.CharField(max_length=200)
    telefono = models.CharField('teléfono', max_length=40, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    recibe = models.CharField('residuos que recibe (según la fuente)', max_length=300, blank=True)
    fuente = models.CharField(max_length=10, choices=FuentePunto.choices, default=FuentePunto.MANUAL)
    id_externo = models.CharField('identificador en la fuente', max_length=40, blank=True)
    verificado_en = models.DateField('fecha de la información', null=True, blank=True)
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    residuos = models.ManyToManyField(Residuo, through='ResiduoPunto', related_name='puntos', blank=True)

    class Meta:
        db_table = 'punto_entrega'
        ordering = ['localidad', 'nombre']
        indexes = [models.Index(fields=['localidad'], name='ix_punto_localidad'),
                   models.Index(fields=['fuente', 'id_externo'], name='ix_punto_fuente_externo')]

    def __str__(self):
        return self.nombre

    @property
    def tiene_ubicacion(self):
        return self.latitud is not None and self.longitud is not None

    def como_llegar(self):
        """Enlace de indicaciones en Google Maps (se abre fuera de EcoParce; no enviamos la ubicación del visitante)."""
        from urllib.parse import quote
        if self.tiene_ubicacion:
            return f'https://www.google.com/maps/dir/?api=1&destination={self.latitud},{self.longitud}'
        return 'https://www.google.com/maps/search/?api=1&query=' + quote(f'{self.direccion}, {self.localidad}, Bogotá')


class ResiduoPunto(models.Model):
    residuo = models.ForeignKey(Residuo, on_delete=models.CASCADE)
    punto = models.ForeignKey(PuntoEntrega, on_delete=models.CASCADE)

    class Meta:
        db_table = 'residuo_punto'
        constraints = [models.UniqueConstraint(fields=['residuo', 'punto'], name='uq_residuo_punto')]
