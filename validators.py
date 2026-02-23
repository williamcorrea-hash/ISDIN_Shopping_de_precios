def precio_valido(precio):
    return precio is not None and isinstance(precio, int) and precio > 1