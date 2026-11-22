from django import forms

from .models import OpcionTrivia, PreguntaTrivia


class PreguntaForm(forms.ModelForm):
    class Meta:
        model = PreguntaTrivia
        fields = ['enunciado', 'dificultad', 'explicacion']
        widgets = {'enunciado': forms.Textarea(attrs={'rows': 2, 'maxlength': 300}),
                   'explicacion': forms.Textarea(attrs={'rows': 3, 'maxlength': 500})}


class OpcionesForm(forms.Form):
    """Hasta cuatro opciones; se valida RN-07 (2 a 4 opciones y una sola correcta)."""
    correcta = forms.ChoiceField(choices=[(str(i), 'ABCD'[i - 1]) for i in range(1, 5)], widget=forms.RadioSelect,
                                 label='Opción correcta', error_messages={'required': 'Marca la opción correcta.'})

    def __init__(self, *args, pregunta=None, **kwargs):
        super().__init__(*args, **kwargs)
        existentes = {o.orden: o for o in pregunta.opciones.all()} if pregunta and pregunta.pk else {}
        for i in range(1, 5):
            o = existentes.get(i)
            self.fields[f'opcion_{i}'] = forms.CharField(label=f'Opción {"ABCD"[i - 1]}', max_length=200, required=False,
                                                         initial=o.texto if o else '')
            if o and o.es_correcta:
                self.fields['correcta'].initial = str(i)

    def filas(self):
        radios = list(self['correcta'])
        return [(radios[i - 1], self[f'opcion_{i}']) for i in range(1, 5)]

    def textos(self):
        return [(i, (self.cleaned_data.get(f'opcion_{i}') or '').strip()) for i in range(1, 5)]

    def clean(self):
        datos = super().clean()
        llenas = [i for i, t in self.textos() if t]
        if len(llenas) < 2:
            raise forms.ValidationError('Escribe al menos dos opciones (RN-07).')
        correcta = datos.get('correcta')
        if correcta and int(correcta) not in llenas:
            self.add_error('correcta', 'La opción marcada como correcta está vacía.')
        return datos

    def guardar(self, pregunta):
        pregunta.opciones.all().delete()
        orden = 1
        correcta = int(self.cleaned_data['correcta'])
        for i, texto in self.textos():
            if texto:
                OpcionTrivia.objects.create(pregunta=pregunta, texto=texto, es_correcta=(i == correcta), orden=orden)
                orden += 1
