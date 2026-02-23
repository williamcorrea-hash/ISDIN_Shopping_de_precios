from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def limpiar_precio(texto):
    if not texto:
        return None
    return int(re.sub(r"[^\d]", "", texto))

def extraer_medipiel(url: str, driver=None, wait=None):
    if driver is None:
        raise Exception("Medipiel requiere Selenium driver (no se pasó driver)")

    if wait is None:
        wait = WebDriverWait(driver, 20)

    driver.get(url)

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


