import re
import unicodedata


def normalizar(texto):
    """Minúsculas, sin tildes ni signos y con un solo espacio: «Botellá  PET!» -> «botella pet»."""
    texto = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode('ascii').lower()
    texto = re.sub(r'[^a-z0-9ñ ]+', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()
