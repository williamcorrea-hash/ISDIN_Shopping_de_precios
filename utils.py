import unicodedata
import re

def normalizar_tienda(nombre):
    if not nombre:
        return None

    # 1. Pasar a minúsculas y quitar espacios extremos
    nombre = nombre.strip().lower()

    # 2. Quitar tildes y caracteres especiales
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = nombre.encode("ascii", "ignore").decode("ascii")

    # 3. Quitar _ repetidos y al inicio/final
    nombre = re.sub(r"_+", "_", nombre).strip("_")

    # 4. Si son dos palabras, unirlas sin espacio
    palabras = nombre.split()
    if len(palabras) == 2:
        nombre = "".join(palabras)

    nombre = nombre.replace("_", "")

    return nombre

