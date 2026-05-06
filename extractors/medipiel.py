from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException  # Importamos esto para manejar el error gigante
import re
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def limpiar_precio(texto):
    if not texto:
        return None
    return int(re.sub(r"[^\d]", "", str(texto)))

def extraer_medipiel(url: str, driver=None, wait=None):
    if driver is None:
        raise Exception("Medipiel requiere Selenium driver (no se pasó driver)")

    if wait is None:
        wait = WebDriverWait(driver, 20)

    try:
        driver.get(url)
        
        # Pausa breve para permitir que la página cargue los botones de React/VTEX
        time.sleep(3)

        # ==========================================
        # 1. VERIFICACIÓN DE PRODUCTO AGOTADO
        # ==========================================
        # Buscamos textos que digan "agotado" o "no disponible" ignorando mayúsculas/minúsculas
        agotado = driver.find_elements(
            By.XPATH, 
            "//*[contains(translate(text(), 'AGOTADO', 'agotado'), 'agotado') or contains(translate(text(), 'NO DISPONIBLE', 'no disponible'), 'no disponible')]"
        )
        
        if len(agotado) > 0:
            print(f"[INFO] Producto Agotado en Medipiel: {url}")
            return 0, 0, "COP"  # Retornamos 0 como pediste

        # ==========================================
        # 2. EXTRACCIÓN DE PRECIO NORMAL
        # ==========================================
        # Si llega aquí, es porque NO está agotado, así que esperamos el precio
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "span.vtex-store-components-3-x-currencyInteger")
            )
        )
        time.sleep(1)

        precio_normal = None
        precio_oferta = None
        moneda = "COP"

        # Normal (tachado)
        try:
            normal_parts = driver.find_elements(
                By.CSS_SELECTOR,
                ".vtex-store-components-3-x-listPrice span.vtex-store-components-3-x-currencyInteger"
            )
            if len(normal_parts) >= 2:
                precio_normal = limpiar_precio(normal_parts[0].text + normal_parts[1].text)
        except:
            pass

        # Oferta (actual)
        try:
            oferta_parts = driver.find_elements(
                By.CSS_SELECTOR,
                ".vtex-store-components-3-x-sellingPrice span.vtex-store-components-3-x-currencyInteger"
            )
            if len(oferta_parts) >= 2:
                precio_oferta = limpiar_precio(oferta_parts[0].text + oferta_parts[1].text)
        except:
            pass

        if precio_normal is None and precio_oferta is not None:
            precio_normal = precio_oferta
            precio_oferta = None

        return precio_normal, precio_oferta, moneda

    # ==========================================
    # 3. MANEJO DE ERRORES (Adiós a los crasheos feos)
    # ==========================================
    except TimeoutException:
        # Si esperó los 20 segundos y no encontró el precio, evitamos el pantallazo de error
        print(f"[ALERTA] Timeout buscando precio en Medipiel: {url}")
        
        # Último chequeo de emergencia por si el "Agotado" estaba oculto en el código:
        if "agotado" in driver.page_source.lower() or "no disponible" in driver.page_source.lower():
            print(f"[INFO] Producto detectado como Agotado en revisión profunda: {url}")
            return 0, 0, "COP"
            
        return None, None, None

    except Exception as e:
        print(f"[ERROR CRÍTICO] Medipiel: {str(e)[:100]}...") # Solo imprimimos un pedacito del error para no saturar
        return None, None, None