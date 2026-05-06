def precio_valido(precio):
    # Cambiamos precio > 1 por precio >= 0 para que acepte los agotados
    return precio is not None and isinstance(precio, int) and precio >= 0