import requests
from bs4 import BeautifulSoup
import re
import urllib3
import json
import time

# Ocultar las advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def limpiar_precio(texto):
    """Limpia el texto y devuelve solo los números como entero."""
    if not texto:
        return None
    return int(re.sub(r"[^\d]", "", str(texto)))

def extraer_linea_estetica(url, driver=None, wait=None):
    html_content = ""
    
    try:
        # ==========================================
        # CONTROL DE NAVEGACIÓN (SELENIUM VS REQUESTS)
        # ==========================================
        if driver is not None:
            # Si el orquestador nos manda el navegador, lo usamos para evadir el 403
            driver.get(url)
            time.sleep(3)  # Damos 3 segundos para que pase cualquier pantalla de validación
            html_content = driver.page_source
        else:
            # Si no hay navegador, intentamos con requests tradicional
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            }
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            if response.status_code != 200:
                print(f"[ALERTA] Bloqueo o error {response.status_code} en URL: {url}")
                return None, None, None
            html_content = response.text

        # ==========================================
        # PARSEO Y EXTRACCIÓN DE DATOS
        # ==========================================
        soup = BeautifulSoup(html_content, "html.parser")

        # MÉTODO 1: JSON-LD (El método SEO invisible)
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                items = []
                if isinstance(data, dict):
                    if "@graph" in data:
                        items = data["@graph"]
                    else:
                        items = [data]
                elif isinstance(data, list):
                    items = data
                    
                for item in items:
                    if item.get("@type") == "Product" or item.get("@type") == ["Product"]:
                        offers = item.get("offers", {})
                        if isinstance(offers, list) and len(offers) > 0:
                            offers = offers[0]
                            
                        precio_seo = offers.get("price")
                        if precio_seo:
                            precio_final = int(float(precio_seo))
                            return precio_final, precio_final, "COP"
            except json.JSONDecodeError:
                pass 

        # MÉTODO 2: Búsqueda Visual HTML (Respaldo)
        contenedor_principal = soup.select_one(".summary.entry-summary") or soup.find("div", {"class": "product"})
        
        if not contenedor_principal:
            print(f"[ALERTA] No se encontró la caja del producto en HTML: {url}")
            return None, None, None

        dele = contenedor_principal.find("del")
        ins = contenedor_principal.find("ins")

        if ins and dele:
            precio_normal = limpiar_precio(dele.get_text())
            precio_descuento = limpiar_precio(ins.get_text())
            return precio_normal, precio_descuento, "COP"
        else:
            precio_bdi = contenedor_principal.select_one("p.price bdi") or contenedor_principal.select_one(".woocommerce-Price-amount bdi")
            if precio_bdi:
                precio_val = limpiar_precio(precio_bdi.get_text())
                return precio_val, precio_val, "COP"

        print(f"[ALERTA] Se abrió la página pero no se detectaron precios: {url}")
        return None, None, None

    except Exception as e:
        print(f"[ERROR CRÍTICO] Falló el scraper en {url}: {e}")
        
    return None, None, None