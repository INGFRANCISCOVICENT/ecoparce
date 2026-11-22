from django import forms

from apps.contenidos.models import Guia

from .models import CodigoQR, Institucion, TipoDestino


class CodigoQRForm(forms.ModelForm):
    class Meta:
        model = CodigoQR
        fields = ['destino_tipo', 'guia', 'institucion', 'ubicacion']
        widgets = {'ubicacion': forms.TextInput(attrs={'placeholder': 'Ej.: Punto ecológico · Torre 3'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['guia'].queryset = Guia.publicadas.all()
        self.fields['guia'].required = False
        self.fields['institucion'].queryset = Institucion.objects.filter(activo=True)
        self.fields['institucion'].required = False

    def clean(self):
        datos = super().clean()
        if datos.get('destino_tipo') == TipoDestino.GUIA and not datos.get('guia'):
            self.add_error('guia', 'Elige la guía publicada a la que lleva el código.')
        if datos.get('destino_tipo') != TipoDestino.GUIA:
            datos['guia'] = None
        return datos


class InstitucionForm(forms.ModelForm):
    class Meta:
        model = Institucion
        fields = ['nombre', 'tipo', 'contacto_nombre', 'contacto_correo']
