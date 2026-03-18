import os
import re
import time


PRECIO_REGEX = re.compile(r'\$\s*(\d{1,3}(?:\.\d{3})+)')


def limpiar_precio_token(token):
    if token is None:
        return None

    token = str(token).strip()
    token = re.sub(r"[^\d\.]", "", token)

    if not token:
        return None

    partes = token.split(".")
    if len(partes[0]) <= 3 and all(len(p) == 3 for p in partes[1:]):
        return int("".join(partes))

    return None


def extraer_precios_texto(texto):
    if not texto:
        return []

    tokens = PRECIO_REGEX.findall(texto)
    valores = [limpiar_precio_token(t) for t in tokens]
    valores = [v for v in valores if v is not None]
    valores = [v for v in valores if 10000 <= v <= 500000]

    return list(dict.fromkeys(valores))


def guardar_debug(url, body_text, page_source):
    try:
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)

        safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:80]
        txt_path = os.path.join(logs_dir, f"pasteur_debug_{safe_name}.txt")
        html_path = os.path.join(logs_dir, f"pasteur_debug_{safe_name}.html")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("URL:\n")
            f.write(url + "\n\n")
            f.write("BODY_TEXT:\n")
            f.write(body_text)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page_source)
    except Exception:
        pass


def cerrar_banners(driver):
    from selenium.webdriver.common.by import By

    posibles = [
        "//button[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ACEPTAR')]",
        "//button[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'CERRAR')]",
        "//button[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ENTENDIDO')]",
        "//a[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'CERRAR')]",
    ]

    for xp in posibles:
        try:
            elems = driver.find_elements(By.XPATH, xp)
            for elem in elems[:3]:
                if elem.is_displayed():
                    elem.click()
                    time.sleep(1)
        except Exception:
            pass


def contiene_indicador_descuento(texto):
    if not texto:
        return False

    t = texto.lower()

    indicadores = [
        "antes",
        "ahora",
        "descuento",
        "oferta",
        "promoción",
        "promocion",
        "sale",
        "regular",
        "tachado",
        "save",
        "%",
    ]

    return any(x in t for x in indicadores)


def es_texto_auxiliar_no_descuento(texto):
    """
    Filtra textos como:
    - G $64.801
    - ML $2.841,94
    - valor por unidad / referencia auxiliar
    """
    if not texto:
        return False

    t = texto.lower()

    patrones_aux = [
        r"\bg\s*\$",
        r"\bgr\b",
        r"\bgramo",
        r"\bgramos",
        r"\bml\s*\$",
        r"\bonz",
        r"\boz\b",
        r"\bkg\s*\$",
        r"\blt\s*\$",
        r"\bl\s*\$",
        r"\bpor g\b",
        r"\bpor ml\b",
        r"\bcuota",
        r"\bcuotas",
        r"\bunidad",
        r"\bunidades",
    ]

    for p in patrones_aux:
        if re.search(p, t):
            return True

    return False


def extraer_precio_principal_desde_texto(texto):
    """
    Devuelve solo el precio principal visible.
    Si aparecen varios, toma el mayor razonable como precio normal.
    """
    vals = extraer_precios_texto(texto)
    if not vals:
        return None

    return max(vals)


def extraer_descuento_desde_texto(texto):
    """
    Solo devuelve precio oferta si hay evidencia de descuento real.
    No toma precios por gramo/ml.
    """
    if not texto:
        return None

    if es_texto_auxiliar_no_descuento(texto) and not contiene_indicador_descuento(texto):
        return None

    vals = extraer_precios_texto(texto)
    if len(vals) < 2:
        return None

    # Si hay señal de descuento, el menor puede ser oferta
    if contiene_indicador_descuento(texto):
        menor = min(vals)
        mayor = max(vals)
        if menor < mayor:
            return menor

    return None


def extraer_pasteur(url, driver=None, wait=None):
    if driver is None:
        raise Exception("Pasteur requiere Selenium driver (no se pasó driver)")

    from selenium.webdriver.common.by import By

    driver.get(url)
    time.sleep(5)

    cerrar_banners(driver)
    time.sleep(2)

    try:
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(1.2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.2)
    except Exception:
        pass

    textos_candidatos = []

    # 1) bloque de compra / precio
    xpaths = [
        "//*[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'AGREGAR AL CARRITO')]",
        "//*[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PRECIO')]",
    ]

    for xp in xpaths:
        try:
            elems = driver.find_elements(By.XPATH, xp)
            for elem in elems:
                try:
                    for nivel in range(1, 6):
                        anc = elem.find_element(By.XPATH, "./" + "../" * nivel)
                        txt = anc.text.strip()
                        if "$" in txt:
                            textos_candidatos.append(txt)
                except Exception:
                    pass
        except Exception:
            pass

    # 2) clases tipo VTEX
    selectores = [
        'div[class*="price-info"]',
        'div[class*="flexColChild--price"]',
        'div[class*="selling-price"]',
        'div[class*="price"]',
    ]

    for sel in selectores:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                txt = elem.text.strip()
                if "$" in txt:
                    textos_candidatos.append(txt)
        except Exception:
            pass

    # 3) resolver
    mejor_precio_normal = None
    mejor_precio_oferta = None

    for texto in textos_candidatos:
        precio_normal = extraer_precio_principal_desde_texto(texto)
        precio_oferta = extraer_descuento_desde_texto(texto)

        if precio_normal is not None:
            if mejor_precio_normal is None:
                mejor_precio_normal = precio_normal

            # prioriza bloque con descuento real si alguna vez aparece
            if precio_oferta is not None and precio_oferta < precio_normal:
                mejor_precio_normal = precio_normal
                mejor_precio_oferta = precio_oferta
                break

            # si no hay descuento real, conserva solo precio normal
            if mejor_precio_normal is None or precio_normal > mejor_precio_normal:
                mejor_precio_normal = precio_normal

    if mejor_precio_normal is not None:
        return mejor_precio_normal, mejor_precio_oferta, "COP"

    body_text = driver.find_element(By.TAG_NAME, "body").text
    guardar_debug(url, body_text, driver.page_source)

    raise Exception("No se encontró precio en Pasteur")