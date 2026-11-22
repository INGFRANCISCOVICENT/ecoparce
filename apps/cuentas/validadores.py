import re
import unicodedata

from django.core.exceptions import ValidationError


def _normalizar(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', (texto or '').strip().lower())
        if not unicodedata.combining(c)
    )


class ClaveSeguraValidator:
    """Exige letra minúscula, mayúscula, número, carácter especial y ausencia de correo/nombre."""

    def validate(self, password, user=None):
        errores = []
        if len(password) <= 8:
            errores.append('Debe tener más de 8 caracteres (mínimo 9).')
        if not re.search(r'[a-z]', password):
            errores.append('Debe incluir al menos una letra minúscula.')
        if not re.search(r'[A-Z]', password):
            errores.append('Debe incluir al menos una letra mayúscula.')
        if not re.search(r'\d', password):
            errores.append('Debe incluir al menos un número.')
        if not re.search(r'[^A-Za-z0-9\s]', password):
            errores.append('Debe incluir al menos un carácter especial (ej. ! @ # $ % - _).')

        if user is not None:
            low = _normalizar(password)
            correo = _normalizar(getattr(user, 'correo', ''))
            nombre = _normalizar(getattr(user, 'nombre', ''))
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
                errores.append('La contraseña no puede contener tu correo ni tu nombre.')

        if errores:
            raise ValidationError(errores)

    def get_help_text(self):
        return (
            'Usa más de 8 caracteres con mayúscula, minúscula, número y carácter especial, '
            'sin incluir tu correo ni tu nombre.'
        )
