import io
import secrets

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.db import models
from django.urls import reverse

ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # sin 0/O ni 1/I para evitar confusiones


class TipoInstitucion(models.TextChoices):
    CONJUNTO = 'CONJUNTO', 'Conjunto residencial'
    COLEGIO = 'COLEGIO', 'Colegio'
    UNIVERSIDAD = 'UNIVERSIDAD', 'Universidad'
    EMPRESA = 'EMPRESA', 'Empresa'
    PUNTO_ECOLOGICO = 'PUNTO_ECOLOGICO', 'Punto ecológico'
    OTRO = 'OTRO', 'Otro'


class Institucion(models.Model):
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TipoInstitucion.choices, default=TipoInstitucion.CONJUNTO)
    contacto_nombre = models.CharField('nombre del contacto', max_length=120, blank=True)
    contacto_correo = models.EmailField('correo del contacto', max_length=254, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'institucion'
        ordering = ['nombre']
        constraints = [models.CheckConstraint(condition=models.Q(tipo__in=TipoInstitucion.values), name='ck_institucion_tipo')]

    def __str__(self):
        return self.nombre


class TipoDestino(models.TextChoices):
    INICIO = 'INICIO', 'Página de inicio'
    GUIA = 'GUIA', 'Una guía'
    BUSCADOR = 'BUSCADOR', 'Buscador'
    TRIVIA = 'TRIVIA', 'Trivia'


class CodigoQR(models.Model):
    codigo_corto = models.CharField(max_length=8, unique=True, editable=False)
    destino_tipo = models.CharField('lleva a', max_length=12, choices=TipoDestino.choices, default=TipoDestino.GUIA)
    guia = models.ForeignKey('contenidos.Guia', verbose_name='guía', null=True, blank=True, on_delete=models.RESTRICT, related_name='codigos_qr')
    institucion = models.ForeignKey(Institucion, verbose_name='institución', null=True, blank=True, on_delete=models.SET_NULL, related_name='codigos_qr')
    ubicacion = models.CharField('ubicación física', max_length=160)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='+')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'codigo_qr'
        ordering = ['-creado_en']
        verbose_name = 'código QR'
        verbose_name_plural = 'códigos QR'
        constraints = [
            models.CheckConstraint(condition=models.Q(destino_tipo__in=TipoDestino.values), name='ck_qr_destino'),
            models.CheckConstraint(condition=~models.Q(destino_tipo='GUIA') | models.Q(guia__isnull=False), name='ck_qr_guia'),
        ]

    def __str__(self):
        return self.codigo_corto

    def save(self, *args, **kwargs):
        if not self.codigo_corto:
            while True:
                codigo = ''.join(secrets.choice(ALFABETO) for _ in range(8))
                if not CodigoQR.objects.filter(codigo_corto=codigo).exists():
                    self.codigo_corto = codigo
                    break
        super().save(*args, **kwargs)

    def url_corta(self):
        return settings.SITE_URL.rstrip('/') + reverse('qr:redirigir', args=[self.codigo_corto])

    def destino_url(self):
        """URL del destino; si la guía no está publicada, el inicio."""
        if self.destino_tipo == TipoDestino.GUIA and self.guia and self.guia.publicado:
            return self.guia.get_absolute_url()
        return {TipoDestino.BUSCADOR: reverse('buscador:buscar'), TipoDestino.TRIVIA: reverse('trivia:inicio')}.get(
            self.destino_tipo, reverse('core:inicio'))

    def destino_texto(self):
        if self.destino_tipo == TipoDestino.GUIA and self.guia:
            return self.guia.titulo
        return self.get_destino_tipo_display()

    def generar_imagen(self, formato='png'):
        """Genera el QR de la URL corta en PNG o SVG (RF-07)."""
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=3)
        qr.add_data(self.url_corta())
        qr.make(fit=True)
        buf = io.BytesIO()
        if formato == 'svg':
            qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(buf)
        else:
            qr.make_image(fill_color='#14261C', back_color='white').save(buf, format='PNG')
        return buf.getvalue()

    def registrar_escaneo(self, tipo_dispositivo):
        return Escaneo.objects.create(codigo_qr=self, tipo_dispositivo=tipo_dispositivo)


class TipoDispositivo(models.TextChoices):
    MOVIL = 'MOVIL', 'Teléfono'
    TABLET = 'TABLET', 'Tablet'
    ESCRITORIO = 'ESCRITORIO', 'Computador'


class Escaneo(models.Model):
    """Lectura anónima de un QR (RN-08): no se guarda IP, cookies ni datos personales."""
    codigo_qr = models.ForeignKey(CodigoQR, on_delete=models.CASCADE, related_name='escaneos')
    fecha_hora = models.DateTimeField(auto_now_add=True)
    tipo_dispositivo = models.CharField(max_length=10, choices=TipoDispositivo.choices, default=TipoDispositivo.MOVIL)

    class Meta:
        db_table = 'escaneo'
        ordering = ['-fecha_hora']
        indexes = [models.Index(fields=['codigo_qr', 'fecha_hora'], name='ix_escaneo_qr_fecha')]
        constraints = [models.CheckConstraint(condition=models.Q(tipo_dispositivo__in=TipoDispositivo.values),
                                              name='ck_escaneo_dispositivo')]


def tipo_dispositivo(user_agent):
    """Clasifica el dispositivo a partir del agente de usuario, sin guardarlo."""
    ua = (user_agent or '').lower()
    if 'ipad' in ua or 'tablet' in ua or ('android' in ua and 'mobile' not in ua):
        return TipoDispositivo.TABLET
    if 'mobi' in ua or 'iphone' in ua or 'android' in ua:
        return TipoDispositivo.MOVIL
    return TipoDispositivo.ESCRITORIO
