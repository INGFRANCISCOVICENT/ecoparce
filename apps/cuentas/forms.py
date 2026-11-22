from django import forms

from .models import Rol, Usuario

ROLES_PERSONAL = [(Rol.CONTENIDO, Rol.CONTENIDO.label), (Rol.SISTEMA, Rol.SISTEMA.label)]


class AdministradorForm(forms.Form):
    """RF-15: autorizar a una persona como administradora. Entrará con su propia cuenta de Google."""
    nombre = forms.CharField(max_length=120)
    correo = forms.EmailField(label='Correo de Google', help_text='La persona debe ingresar con una cuenta de Google con este mismo correo.')
    rol = forms.ChoiceField(choices=ROLES_PERSONAL)

    def clean_correo(self):
        correo = self.cleaned_data['correo'].strip().lower()
        existente = Usuario.objects.filter(correo=correo).first()
        if existente and existente.es_personal:
            raise forms.ValidationError('Esa persona ya es administradora.')
        self.existente = existente
        return correo


class UsuarioEditarForm(forms.ModelForm):
    rol = forms.ChoiceField(choices=Rol.choices)

    class Meta:
        model = Usuario
        fields = ['nombre', 'rol', 'is_active']
        labels = {'is_active': 'Cuenta activa'}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor

    def clean(self):
        datos = super().clean()
        if self.instance.pk == getattr(self.editor, 'pk', None):
            if not datos.get('is_active'):
                self.add_error('is_active', 'No puedes desactivar tu propia cuenta.')
            if datos.get('rol') != Rol.SISTEMA:
                self.add_error('rol', 'No puedes quitarte el rol de administrador del sistema.')
        quedan = Usuario.objects.filter(rol=Rol.SISTEMA, is_active=True).exclude(pk=self.instance.pk).exists()
        if not quedan and (datos.get('rol') != Rol.SISTEMA or not datos.get('is_active')):
            raise forms.ValidationError('Debe quedar al menos un administrador del sistema activo.')
        return datos


class AutorizacionForm(forms.Form):
    acepto = forms.BooleanField(
        label='Acepto los Términos y Condiciones, autorizo el tratamiento de mis datos según la Política de Privacidad y confirmo ser mayor de 14 años o tener permiso de mi madre, padre o acudiente.',
        error_messages={'required': 'Para usar una cuenta debes aceptar los términos y el tratamiento de datos.'})
    acepta_marketing = forms.BooleanField(
        required=False,
        label='Opcional: quiero recibir novedades educativas y tips de reciclaje por correo (puedes darte de baja en cualquier momento).')


class EliminarCuentaForm(forms.Form):
    confirmacion = forms.CharField(label='Escribe ELIMINAR para confirmar', max_length=10)

    def clean_confirmacion(self):
        if self.cleaned_data['confirmacion'].strip().upper() != 'ELIMINAR':
            raise forms.ValidationError('Escribe la palabra ELIMINAR.')
        return 'ELIMINAR'


def dominio_recibe_correo(correo):
    """Comprueba que el dominio tenga registros MX (o A) reales, como en CiudadReporta."""
    import dns.exception
    import dns.resolver
    dominio = correo.rsplit('@', 1)[-1]
    resolver = dns.resolver.Resolver()
    resolver.lifetime = 4
    for tipo in ('MX', 'A'):
        try:
            if resolver.resolve(dominio, tipo):
                return True
        except dns.resolver.NXDOMAIN:
            return False
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            continue
        except dns.exception.DNSException:
            return True  # si el DNS falla temporalmente no se bloquea el registro
    return False


class RegistroForm(forms.Form):
    """Campos adicionales del registro con correo. Todas las casillas van sin marcar (Ley 1581, art. 9)."""
    nombre = forms.CharField(
        label='Nombre (opcional)', max_length=120, required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'name', 'placeholder': 'Si lo dejas vacío, lo tomamos de tu correo'}),
    )
    acepta_datos = forms.BooleanField(
        label='Acepto los Términos y Condiciones y autorizo el tratamiento de mis datos personales según la Política de Privacidad.',
        error_messages={'required': 'Debes aceptar los términos y autorizar el tratamiento de datos para crear la cuenta.'})
    mayor_edad = forms.BooleanField(
        label='Soy mayor de 14 años o cuento con el permiso expreso de mi madre, padre o acudiente.',
        error_messages={'required': 'Confirma tu edad o el permiso expreso de tu acudiente.'})
    acepta_marketing = forms.BooleanField(
        required=False,
        label='Opcional: quiero recibir novedades educativas y tips de reciclaje por correo (puedes darte de baja en cualquier momento).')

    def clean(self):
        import re
        from .validadores import _normalizar
        datos = super().clean()
        clave = datos.get('password1') or ''
        if clave:
            low = _normalizar(clave)
            correo = _normalizar(datos.get('email'))
            nombre = _normalizar(datos.get('nombre'))
            partes = []
            if correo:
                partes.append(correo)
                local = correo.split('@')[0]
                if len(local) >= 3:
                    partes.append(local)
            for palabra in re.split(r'[\s._-]+', nombre):
                if len(palabra) >= 3:
                    partes.append(palabra)
            if any(p in low for p in partes):
                self.add_error('password1', 'La contraseña no puede contener tu correo ni tu nombre.')
        return datos

    def signup(self, request, user):
        from django.conf import settings

        from apps.core.seguridad import evento

        from .models import Consentimiento
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            nombre = user.correo.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ').title()[:120]
        user.nombre = nombre
        user.rol = Rol.VISITANTE
        user.save(update_fields=['nombre', 'rol'])
        Consentimiento.objects.update_or_create(
            usuario=user,
            version=settings.VERSION_AVISO_PRIVACIDAD,
            defaults={
                'acepta_terminos': True,
                'mayor_edad_o_acudiente': True,
                'acepta_marketing': bool(self.cleaned_data.get('acepta_marketing')),
            },
        )
        evento('cuenta_creada_correo', request, user)


from allauth.account.forms import LoginForm as _LoginForm  # noqa: E402


class IngresoForm(_LoginForm):
    """Formulario de ingreso con correo: sin el enlace de ayuda duplicado (la plantilla ya lo muestra)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].help_text = ''
        self.fields['login'].widget.attrs.update({'autocomplete': 'email', 'placeholder': 'tu-correo@ejemplo.com'})
