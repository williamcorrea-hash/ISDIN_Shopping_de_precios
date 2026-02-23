from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def limpiar_precio(texto):
    if not texto:
        return None
    numeros = re.sub(r"[^\d]", "", texto)
    if not numeros:
        return None
    return int(numeros)

def extraer_cruz_verde(url, driver=None, wait=None):
    if driver is None:
        raise Exception("Cruz Verde requiere Selenium driver (no se pasó driver)")

    if wait is None:
        wait = WebDriverWait(driver, 20)

    driver.get(url)

    wait.until(lambda d: d.find_element(By.CLASS_NAME, "text-prices").text.strip() != "")

    precio_desc_elem = driver.find_element(By.CLASS_NAME, "text-prices")
    precio_descuento = limpiar_precio(precio_desc_elem.text)
    if precio_descuento is None:
        raise ValueError("Precio descuento vacío o inválido")

    try:
        precio_normal_elem = driver.find_element(By.CLASS_NAME, "line-through")
        precio_normal = limpiar_precio(precio_normal_elem.text) or precio_descuento
    except:
        precio_normal = precio_descuento

    return precio_normal, precio_descuento, "COP"
