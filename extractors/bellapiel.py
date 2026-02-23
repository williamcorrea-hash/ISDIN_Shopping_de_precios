import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extraer_bellapiel(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=15, verify=False)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    def leer_precio(selector):
        container = soup.select_one(selector)
        if not container:
            return None

        partes = container.select("span.vtex-product-price-1-x-currencyInteger")
        if not partes:
            return None

        numero = "".join(p.text.strip() for p in partes)
        return int(numero)

    # Precio normal (tachado)
    precio_normal = leer_precio(
        "span.vtex-product-price-1-x-listPriceValue"
    )

    # Precio actual (oferta)
    precio_actual = leer_precio(
        "span.vtex-product-price-1-x-sellingPriceValue"
    )

    if precio_actual is None:
        raise Exception("No se encontró precio en Bellapiel")

    if precio_normal is None:
        precio_normal = precio_actual
        precio_oferta = None
    else:
        precio_oferta = precio_actual

    return precio_normal, precio_oferta, "COP"
