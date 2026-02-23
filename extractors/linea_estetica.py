import requests
from bs4 import BeautifulSoup
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def limpiar_precio(texto):
    return int(re.sub(r"[^\d]", "", texto))


def extraer_linea_estetica(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=15, verify=False)

    if response.status_code != 200:
        return None, None, None

    soup = BeautifulSoup(response.text, "html.parser")

    precio_normal = None
    precio_descuento = None

    # -------------------------
    # Precio en oferta (<ins>)
    # -------------------------
    ins = soup.find("ins")
    if ins:
        bdi = ins.find("bdi")
        if bdi:
            precio_descuento = limpiar_precio(bdi.get_text())

    # -------------------------
    # Precio normal (<del>)
    # -------------------------
    dele = soup.find("del")
    if dele:
        bdi = dele.find("bdi")
        if bdi:
            precio_normal = limpiar_precio(bdi.get_text())

    # Si hay descuento
    if precio_descuento:
        if not precio_normal:
            precio_normal = precio_descuento
        return precio_normal, precio_descuento, "COP"

    # -------------------------
    # Caso sin descuento
    # -------------------------
    bdi = soup.select_one(".woocommerce-Price-amount bdi")
    if bdi:
        precio = limpiar_precio(bdi.get_text())
        return precio, precio, "COP"

    return None, None, None
