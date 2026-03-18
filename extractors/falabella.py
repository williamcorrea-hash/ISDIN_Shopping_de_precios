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


def extraer_falabella(url, driver=None, wait=None):
    if driver is None:
        raise Exception("Falabella requiere Selenium driver (no se pasó driver)")

    from selenium.webdriver.common.by import By

    driver.get(url)
    time.sleep(4)

    # ==========================================================
    # 1) BLOQUE PRINCIPAL DEL PDP
    #    Según tu captura:
    #    div[data-variant="PDP_MAIN"]
    # ==========================================================
    bloques = []

    selectores_bloque = [
        'div[data-variant="PDP_MAIN"]',
        'div[id^="testId-pod-prices-"]',
        'div[class*="prices"]',
    ]

    for sel in selectores_bloque:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                txt = elem.text.strip()
                if "$" in txt:
                    bloques.append(elem)
        except Exception:
            pass

    # ==========================================================
    # 2) PRECIO ACTUAL DIRECTO
    #    Según tu captura:
    #    span.copy12.primary.senary...
    # ==========================================================
    precio_actual = None
    precio_tachado = None

    selectores_actual = [
        'div[data-variant="PDP_MAIN"] span[class*="copy12"][class*="primary"]',
        'div[id^="testId-pod-prices-"] span[class*="copy12"][class*="primary"]',
        'span[class*="copy12"][class*="primary"]',
    ]

    for sel in selectores_actual:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                txt = elem.text.strip()
                vals = extraer_precios_texto(txt)
                if vals:
                    precio_actual = vals[0]
                    break
            if precio_actual is not None:
                break
        except Exception:
            pass

    # ==========================================================
    # 3) PRECIO TACHADO DIRECTO
    # ==========================================================
    selectores_tachado = [
        'div[data-variant="PDP_MAIN"] span[class*="line-through"]',
        'div[id^="testId-pod-prices-"] span[class*="line-through"]',
        's',
        'del',
    ]

    for sel in selectores_tachado:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                txt = elem.text.strip()
                vals = extraer_precios_texto(txt)
                if vals:
                    precio_tachado = vals[0]
                    break
            if precio_tachado is not None:
                break
        except Exception:
            pass

    if precio_actual is not None and precio_tachado is not None:
        precio_normal = max(precio_actual, precio_tachado)
        precio_oferta = min(precio_actual, precio_tachado)
        if precio_normal == precio_oferta:
            precio_oferta = None
        return precio_normal, precio_oferta, "COP"

    if precio_actual is not None:
        # intentar sacar el tachado SOLO del mismo bloque
        for bloque in bloques:
            try:
                txt = bloque.text.strip()
                vals = extraer_precios_texto(txt)
                if precio_actual in vals and len(vals) >= 2:
                    precio_normal = max(vals)
                    precio_oferta = min(vals)
                    if precio_normal == precio_oferta:
                        precio_oferta = None
                    return precio_normal, precio_oferta, "COP"
            except Exception:
                pass

        return precio_actual, None, "COP"

    # ==========================================================
    # 4) FALLBACK SOLO SOBRE BLOQUES DEL PANEL DE PRECIOS
    # ==========================================================
    for bloque in bloques:
        try:
            txt = bloque.text.strip()
            vals = extraer_precios_texto(txt)
            if vals:
                if len(vals) == 1:
                    return vals[0], None, "COP"
                return max(vals), min(vals), "COP"
        except Exception:
            pass

    raise Exception("No se encontró precio en Falabella")