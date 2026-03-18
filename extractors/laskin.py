import re
import time


def limpiar_precio(texto):
    if texto is None:
        return None

    numeros = re.sub(r"[^\d]", "", str(texto))
    if not numeros:
        return None

    valor = int(numeros)

    if valor > 9_999_999:
        valor = int(round(valor / 100))

    return valor


def _depurar_valores(valores):
    valores = [v for v in valores if v is not None and v >= 10000]
    if not valores:
        return []

    valores = sorted(set(valores))
    maximo = max(valores)

    filtrados = [v for v in valores if v >= maximo * 0.45]
    if not filtrados:
        filtrados = valores

    return sorted(set(filtrados))


def _resolver_desde_texto(texto):
    matches = re.findall(r'\$\s*[\d\.\,]+', texto)
    valores = [limpiar_precio(x) for x in matches]
    valores = _depurar_valores(valores)

    if not valores:
        return None, None

    if len(valores) == 1:
        return valores[0], None

    return max(valores), min(valores)


def _extraer_requests(url):
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=30, verify=False)
    response.raise_for_status()

    precio_normal, precio_oferta = _resolver_desde_texto(response.text)

    if precio_normal is None:
        raise Exception("No se encontró precio en Laskin")

    return precio_normal, precio_oferta, "COP"


def _extraer_selenium(url, driver, wait):
    from selenium.webdriver.common.by import By

    driver.get(url)
    time.sleep(4)

    selectores_actual = [
        ".price-item--sale",
        ".price__sale .price-item",
        ".price__sale .money",
        ".price .money",
        ".sale-price",
        ".price",
    ]

    selectores_tachado = [
        ".price-item--regular",
        ".price__compare .price-item",
        ".price__compare .money",
        "s .money",
        "del .money",
        "s",
        "del",
    ]

    precio_actual = None
    precio_tachado = None

    for sel in selectores_actual:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                txt = elem.text.strip()
                val = limpiar_precio(txt)
                if val and val >= 10000:
                    precio_actual = val
                    break
            if precio_actual:
                break
        except Exception:
            pass

    for sel in selectores_tachado:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                txt = elem.text.strip()
                val = limpiar_precio(txt)
                if val and val >= 10000:
                    precio_tachado = val
                    break
            if precio_tachado:
                break
        except Exception:
            pass

    if precio_actual and precio_tachado:
        precio_normal = max(precio_actual, precio_tachado)
        precio_oferta = min(precio_actual, precio_tachado)
        if precio_normal == precio_oferta:
            precio_oferta = None
        return precio_normal, precio_oferta, "COP"

    xpaths = [
        "//*[contains(., 'Añadir al carrito') and contains(., '$')]",
        "//*[contains(., 'AHORRA') and contains(., '$')]",
        "//*[contains(., 'Cantidad') and contains(., '$')]",
        "//*[contains(@class, 'price')]",
        "//main",
    ]

    textos_candidatos = []
    for xp in xpaths:
        try:
            elems = driver.find_elements(By.XPATH, xp)
            for elem in elems:
                texto = elem.text.strip()
                if "$" in texto:
                    textos_candidatos.append(texto)
        except Exception:
            pass

    for texto in textos_candidatos:
        precio_normal, precio_oferta = _resolver_desde_texto(texto)
        if precio_normal is not None:
            if precio_oferta is not None and precio_oferta >= precio_normal:
                precio_oferta = None
            return precio_normal, precio_oferta, "COP"

    body_text = driver.find_element(By.TAG_NAME, "body").text
    precio_normal, precio_oferta = _resolver_desde_texto(body_text)

    if precio_normal is None:
        raise Exception("No se encontró precio en Laskin")

    if precio_oferta is not None and precio_oferta >= precio_normal:
        precio_oferta = None

    return precio_normal, precio_oferta, "COP"


def extraer_laskin(url, driver=None, wait=None):
    if driver is not None:
        return _extraer_selenium(url, driver, wait)
    return _extraer_requests(url)