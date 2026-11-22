from django import forms

from .models import Sugerencia


class SugerenciaForm(forms.ModelForm):
    sitio_web = forms.CharField(required=False, label='No llenar', widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))

    class Meta:
        model = Sugerencia
        fields = ['termino', 'comentario']
        widgets = {'termino': forms.TextInput(attrs={'maxlength': 100}),
                   'comentario': forms.Textarea(attrs={'rows': 3, 'maxlength': 300, 'placeholder': '¿Dónde lo encontraste? ¿Qué dudas tienes?'})}
        labels = {'comentario': 'Comentario (opcional)'}

    def clean_termino(self):
        t = self.cleaned_data['termino'].strip()
        if len(t) < 2:
            raise forms.ValidationError('Escribe el nombre del residuo.')
        return t
