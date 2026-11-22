from django import forms

from .models import Contenedor, EstadoContenido, Guia, PuntoEntrega, Residuo, TipoGuia


class GuiaForm(forms.ModelForm):
    class Meta:
        model = Guia
        fields = ['titulo', 'tipo', 'contenedor', 'resumen', 'cuerpo', 'fuente_oficial']
        widgets = {'resumen': forms.Textarea(attrs={'rows': 2, 'maxlength': 300}),
                   'cuerpo': forms.Textarea(attrs={'rows': 12}),
                   'fuente_oficial': forms.TextInput(attrs={'placeholder': 'Ej.: Resolución 2184 de 2019, artículo 4 (MinAmbiente)'})}
        help_texts = {'fuente_oficial': 'Obligatoria para enviar a revisión (RN-02).',
                      'cuerpo': 'Párrafos normales para explicar. Empiece la línea con «+» para lo que sí va y con «-» para lo que no va.'}

    def clean(self):
        datos = super().clean()
        if datos.get('tipo') == TipoGuia.SEPARACION and not datos.get('contenedor'):
            self.add_error('contenedor', 'Una guía de separación debe indicar su contenedor.')
        return datos


class ResiduoForm(forms.ModelForm):
    puntos_entrega = forms.ModelMultipleChoiceField(
        PuntoEntrega.objects.filter(activo=True), required=False, widget=forms.CheckboxSelectMultiple,
        label='Puntos de entrega', help_text='Solo para residuos especiales.')

    class Meta:
        model = Residuo
        fields = ['nombre', 'sinonimos', 'contenedor', 'guia', 'es_especial', 'preparacion']
        widgets = {'preparacion': forms.Textarea(attrs={'rows': 3, 'maxlength': 300}),
                   'sinonimos': forms.TextInput(attrs={'placeholder': 'Ej.: botella PET, envase de gaseosa'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['guia'].queryset = Guia.objects.exclude(estado=EstadoContenido.RETIRADO)
        self.fields['guia'].required = False
        if self.instance.pk:
            self.fields['puntos_entrega'].initial = self.instance.puntos.all()

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        return nombre[:1].upper() + nombre[1:]

    def clean(self):
        """RN-05: un residuo especial va siempre a un punto posconsumo, nunca a una bolsa."""
        datos = super().clean()
        contenedor = datos.get('contenedor')
        if contenedor and contenedor.codigo == Contenedor.POSCONSUMO:
            datos['es_especial'] = True
        elif datos.get('es_especial'):
            self.add_error('contenedor', 'Un residuo especial debe ir a «Punto posconsumo» (RN-05).')
        if datos.get('puntos_entrega') and not datos.get('es_especial'):
            self.add_error('puntos_entrega', 'Solo los residuos especiales tienen puntos de entrega.')
        return datos

    def save(self, commit=True):
        residuo = super().save(commit=commit)
        if commit:
            residuo.puntos.set(self.cleaned_data.get('puntos_entrega') or [])
        return residuo


class PuntoForm(forms.ModelForm):
    class Meta:
        model = PuntoEntrega
        fields = ['nombre', 'direccion', 'localidad', 'barrio', 'horario', 'telefono', 'latitud', 'longitud', 'activo']
        widgets = {'horario': forms.TextInput(attrs={'placeholder': 'Ej.: Lunes a sábado, 8:00 a. m. a 5:00 p. m.'})}
        help_texts = {'latitud': 'Ej.: 4.653332 (clic derecho sobre el lugar en Google Maps para copiarla).',
                      'longitud': 'Ej.: -74.083655'}

    def clean(self):
        datos = super().clean()
        lat, lon = datos.get('latitud'), datos.get('longitud')
        if (lat is None) != (lon is None):
            raise forms.ValidationError('Escribe la latitud y la longitud, o deja ambas vacías.')
        if lat is not None and not (3.7 <= float(lat) <= 4.9 and -74.5 <= float(lon) <= -73.9):
            raise forms.ValidationError('Esas coordenadas no están en Bogotá. Revisa que no estén invertidas.')
        return datos
