"""from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import re
import time
import random
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def limpiar_precio(texto):
    if not texto:
        return None
    texto = re.sub(r"[^\d.,]", "", texto)
    if texto.count(".") > 0 and texto.count(",") == 0:
        texto = texto.replace(".", "")
    elif texto.count(".") > 0 and texto.count(",") > 0:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(",") > 0:
        texto = texto.replace(",", ".")
    try:
        valor = float(texto)
        return int(round(valor))
    except:
        return None

def extraer_farmatodo(url, timeout=30, max_retries=3, driver=None, wait=None):
    
    Extrae precios de Farmatodo de manera más estable.
    - Reintenta hasta max_retries veces si falla
    - Delay aleatorio entre reintentos
    - Maneja productos con y sin oferta
    
    close_driver = False
    if driver is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, timeout)
        close_driver = True

    try:
        for intento in range(1, max_retries + 1):
            try:
                driver.get(url)
                time.sleep(random.uniform(1, 2))  # Delay inicial para render

                # -----------------------------
                # Precio actual
                # -----------------------------
                precio_actual_val = None
                selectores_actual = ["span.box__price--current", "span.price"]
                for sel in selectores_actual:
                    try:
                        wait.until(lambda d: d.find_element(By.CSS_SELECTOR, sel).text.strip() != "")
                        elem = driver.find_element(By.CSS_SELECTOR, sel)
                        texto = elem.text.strip()
                        precio_actual_val = limpiar_precio(texto)
                        if precio_actual_val is not None:
                            break
                    except:
                        continue

                if precio_actual_val is None:
                    raise Exception("No se encontró precio actual")

                # -----------------------------
                # Precio normal / tachado
                # -----------------------------
                try:
                    elem_normal = driver.find_element(By.CSS_SELECTOR, "span.box__price--before")
                    wait.until(lambda d: elem_normal.text.strip() != "")
                    texto_normal = elem_normal.text.strip()
                    precio_normal_val = limpiar_precio(texto_normal)
                    precio_oferta_val = precio_actual_val  # actual es la oferta
                except:
                    # No hay tachado → solo hay precio normal
                    precio_normal_val = precio_actual_val
                    precio_oferta_val = None  # aunque no sea oferta

                return precio_normal_val, precio_oferta_val, "COP"

            except Exception as e:
                print(f"❌ Intento {intento} fallido para {url}: {e}")
                time.sleep(random.uniform(2, 4))  # Delay antes de reintento

        # Si todos los intentos fallan
        return None, None, "COP"

    finally:
        if close_driver:
            driver.quit()"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import re
import time
import random

def limpiar_precio(texto):
    if not texto:
        return None
    texto = re.sub(r"[^\d.,]", "", texto)
    if texto.count(".") > 0 and texto.count(",") == 0:
        texto = texto.replace(".", "")
    elif texto.count(".") > 0 and texto.count(",") > 0:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(",") > 0:
        texto = texto.replace(",", ".")
    try:
        return int(round(float(texto)))
    except:
        return None

def extraer_farmatodo(url, timeout=30, max_retries=3, driver=None, wait=None):
    if driver is None:
        raise Exception("Farmatodo requiere Selenium driver (no se pasó driver)")
    if wait is None:
        wait = WebDriverWait(driver, timeout)

    for intento in range(1, max_retries + 1):
        try:
            driver.get(url)
            time.sleep(random.uniform(1, 2))

            precio_actual_val = None
            selectores_actual = ["span.box__price--current", "span.price"]

            for sel in selectores_actual:
                try:
                    wait.until(lambda d: d.find_element(By.CSS_SELECTOR, sel).text.strip() != "")
                    elem = driver.find_element(By.CSS_SELECTOR, sel)
                    precio_actual_val = limpiar_precio(elem.text.strip())
                    if precio_actual_val is not None:
                        break
                except:
                    continue

            if precio_actual_val is None:
                raise Exception("No se encontró precio actual")

            # Precio normal tachado
            try:
                elem_normal = driver.find_element(By.CSS_SELECTOR, "span.box__price--before")
                wait.until(lambda d: elem_normal.text.strip() != "")
                precio_normal_val = limpiar_precio(elem_normal.text.strip()) or precio_actual_val
                precio_oferta_val = precio_actual_val
            except:
                precio_normal_val = precio_actual_val
                precio_oferta_val = None

            return precio_normal_val, precio_oferta_val, "COP"

        except Exception as e:
            print(f"❌ Farmatodo intento {intento} fallido: {e}")
            time.sleep(random.uniform(2, 4))

    return None, None, "COP"
