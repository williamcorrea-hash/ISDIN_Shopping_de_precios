import requests
from bs4 import BeautifulSoup
import re
import urllib3

# Ocultar las advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def limpiar_precio(texto):
    """Limpia el texto y devuelve solo los números como entero."""
    if not texto:
        return None
    return int(re.sub(r"[^\d]", "", texto))

def extraer_linea_estetica(url):
    headers = {
        # Usamos un User-Agent más completo para evitar bloqueos
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code != 200:
            return None, None, None

        soup = BeautifulSoup(response.text, "html.parser")

        # PASO 1: Localizar el contenedor principal del producto para no traer precios de recomendados
        contenedor_principal = soup.select_one(".summary.entry-summary")
        
        if not contenedor_principal:
            # Si no encuentra el contenedor específico, intentamos con el general de la página
            contenedor_principal = soup.find("div", {"class": "product"})

        if not contenedor_principal:
            return None, None, None

        precio_normal = None
        precio_descuento = None

        # PASO 2: Buscar etiquetas de oferta (<del> para normal, <ins> para oferta)
        # Solo dentro del contenedor principal
        dele = contenedor_principal.find("del")
        ins = contenedor_principal.find("ins")

        if ins and dele:
            # Hay descuento
            precio_normal = limpiar_precio(dele.get_text())
            precio_descuento = limpiar_precio(ins.get_text())
        else:
            # No hay descuento, buscamos el precio único
            precio_bdi = contenedor_principal.select_one(".price bdi")
            if precio_bdi:
                precio_val = limpiar_precio(precio_bdi.get_text())
                precio_normal = precio_val
                precio_descuento = precio_val

        if precio_normal:
            # Retornamos asegurando que si hay descuento, el precio normal debe ser mayor (por sanidad de los datos)
            return precio_normal, precio_descuento, "COP"

    except Exception as e:
        print(f"Error en extraer_linea_estetica con URL {url}: {e}")
        
    return None, None, None