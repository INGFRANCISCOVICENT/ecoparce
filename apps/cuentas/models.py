from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class Rol(models.TextChoices):
    VISITANTE = 'VISITANTE', 'Visitante'
    CONTENIDO = 'CONTENIDO', 'Administrador de contenido'
    SISTEMA = 'SISTEMA', 'Administrador del sistema'


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, correo, nombre, password=None, rol=Rol.VISITANTE):
        if not correo:
            raise ValueError('El correo es obligatorio.')
        usuario = self.model(correo=self.normalize_email(correo).lower(), nombre=nombre, rol=rol)
        if password:
            usuario.set_password(password)
        else:
            usuario.set_unusable_password()  # entra solo con Google
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, nombre, password=None):
        from allauth.account.models import EmailAddress
        usuario = self.create_user(correo, nombre, password, rol=Rol.SISTEMA)
        EmailAddress.objects.update_or_create(user=usuario, email=usuario.correo, defaults={'verified': True, 'primary': True})
        return usuario


class Usuario(AbstractBaseUser):
    """Persona con cuenta: visitante que entró con Google o administrador del panel.
    Navegar, buscar y jugar no exige cuenta; los registros de uso siguen siendo anónimos (RN-08)."""
    correo = models.EmailField('correo', max_length=254, unique=True)
    nombre = models.CharField('nombre', max_length=120)
    password = models.CharField('contraseña', max_length=128, db_column='contrasena_hash')
    last_login = models.DateTimeField('último acceso', null=True, blank=True, db_column='ultimo_acceso')
    rol = models.CharField('rol', max_length=10, choices=Rol.choices, default=Rol.VISITANTE)
    is_active = models.BooleanField('activo', default=True, db_column='activo')
    creado_en = models.DateTimeField('creado en', auto_now_add=True)

    objects = UsuarioManager()
    USERNAME_FIELD = 'correo'
    EMAIL_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'usuario'
        verbose_name = 'usuario'
        ordering = ['nombre']
        constraints = [models.CheckConstraint(condition=models.Q(rol__in=['VISITANTE', 'CONTENIDO', 'SISTEMA']), name='ck_usuario_rol')]

    def __str__(self):
        return self.nombre

    @property
    def iniciales(self):
        partes = self.nombre.split()
        return ''.join(p[0] for p in partes[:2]).upper() or '?'

    @property
    def nombre_corto(self):
        partes = self.nombre.split()
        return f'{partes[0]} {partes[-1][0]}.' if len(partes) > 1 else self.nombre

    @property
    def es_personal(self):
        """Administrador de contenido o del sistema (puede entrar al panel)."""
        return self.is_active and self.rol in (Rol.CONTENIDO, Rol.SISTEMA)

    def es_admin_sistema(self):
        return self.is_active and self.rol == Rol.SISTEMA

    def puede_publicar(self, contenido):
        """RN-03: solo publica un administrador activo que no sea el autor."""
        return self.es_personal and contenido.autor_id != self.pk

    def tiene_mfa(self):
        from allauth.mfa.models import Authenticator
        return Authenticator.objects.filter(user=self, type=Authenticator.Type.TOTP).exists()

    def consentimiento_vigente(self):
        from django.conf import settings
        return self.consentimientos.filter(version=settings.VERSION_AVISO_PRIVACIDAD).exists()


class Consentimiento(models.Model):
    """Autorización de tratamiento de datos personales y términos (Ley 1581 de 2012, Decreto 1074 de 2015)."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='consentimientos')
    version = models.CharField('versión del aviso', max_length=20)
    acepta_terminos = models.BooleanField('acepta términos y condiciones', default=True)
    acepta_marketing = models.BooleanField('acepta novedades por correo', default=False)
    mayor_edad_o_acudiente = models.BooleanField('mayor de 14 años o permiso de acudiente', default=True)
    aceptado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'consentimiento'
        constraints = [models.UniqueConstraint(fields=['usuario', 'version'], name='uq_consentimiento_version')]

    def __str__(self):
        return f'{self.usuario} · {self.version}'
