import re
import time
import random
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def limpiar_precio(texto):
    if texto is None:
        return None

    texto = str(texto).strip()
    if not texto:
        return None

    # deja solo numeros, comas y puntos
    texto = re.sub(r"[^\d,\.]", "", texto)
    if not texto:
        return None

    # Formato Colombia usual:
    # 107.663 -> 107663
    # 107,663 -> 107663
    # 107.663,00 -> 107663
    # 107663 -> 107663
    if "." in texto and "," in texto:
        # 107.663,00 -> 107663.00
        texto = texto.replace(".", "").replace(",", ".")
        try:
            valor = int(round(float(texto)))
        except:
            return None
    elif "." in texto:
        partes = texto.split(".")
        # si parece separador de miles
        if len(partes) > 1 and all(len(p) == 3 for p in partes[1:]):
            texto = "".join(partes)
            try:
                valor = int(texto)
            except:
                return None
        else:
            try:
                valor = int(round(float(texto)))
            except:
                return None
    elif "," in texto:
        partes = texto.split(",")
        # si parece separador de miles
        if len(partes) > 1 and all(len(p) == 3 for p in partes[1:]):
            texto = "".join(partes)
            try:
                valor = int(texto)
            except:
                return None
        else:
            try:
                valor = int(round(float(texto.replace(",", "."))))
            except:
                return None
    else:
        try:
            valor = int(texto)
        except:
            return None

    if valor < 10000 or valor > 500000:
        return None

    return valor


def obtener_texto_elemento(elem):
    try:
        txt = elem.text.strip()
        if txt:
            return txt
    except:
        pass

    try:
        txt = elem.get_attribute("textContent")
        if txt:
            return txt.strip()
    except:
        pass

    return ""


def extraer_valores_desde_texto(texto):
    if not texto:
        return []

    matches = re.findall(r"\$?\s*[\d\.,]{4,}", texto)
    valores = []

    for m in matches:
        val = limpiar_precio(m)
        if val is not None and val not in valores:
            valores.append(val)

    return valores


def extraer_desde_selectores(driver, selectores, contenedor=None):
    valores = []

    for sel in selectores:
        try:
            elems = contenedor.find_elements(By.CSS_SELECTOR, sel) if contenedor else driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                txt = obtener_texto_elemento(e)
                if not txt:
                    continue

                encontrados = extraer_valores_desde_texto(txt)
                for val in encontrados:
                    if val not in valores:
                        valores.append(val)
        except:
            continue

    return sorted(set(valores))


def extraer_precios_json(driver):
    precios_actuales = []
    precios_tachados = []

    def agregar_actual(v):
        val = limpiar_precio(v)
        if val is not None:
            precios_actuales.append(val)

    def agregar_tachado(v):
        val = limpiar_precio(v)
        if val is not None:
            precios_tachados.append(val)

    def recorrer(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = str(k).lower()

                if key in [
                    "price",
                    "sellingprice",
                    "bestprice",
                    "spotprice",
                    "saleprice",
                    "currentprice",
                    "finalprice",
                    "internetprice",
                ]:
                    agregar_actual(v)

                elif key in [
                    "listprice",
                    "highprice",
                    "oldprice",
                    "regularprice",
                    "compareatprice",
                    "originalprice",
                    "beforeprice",
                ]:
                    agregar_tachado(v)

                else:
                    recorrer(v)

        elif isinstance(obj, list):
            for item in obj:
                recorrer(item)

    # JSON-LD
    try:
        scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
        for s in scripts:
            raw = s.get_attribute("innerHTML")
            if not raw or len(raw.strip()) < 5:
                continue
            try:
                data = json.loads(raw)
                recorrer(data)
            except:
                continue
    except:
        pass

    # scripts internos
    try:
        scripts = driver.find_elements(By.TAG_NAME, "script")
        for s in scripts:
            raw = s.get_attribute("innerHTML")
            if not raw:
                continue

            patrones_actual = [
                r'"sellingPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"bestPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"price"\s*:\s*"?([\d\.,]+)"?',
                r'"currentPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"finalPrice"\s*:\s*"?([\d\.,]+)"?',
            ]

            patrones_tachado = [
                r'"listPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"highPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"oldPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"regularPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"originalPrice"\s*:\s*"?([\d\.,]+)"?',
                r'"beforePrice"\s*:\s*"?([\d\.,]+)"?',
            ]

            for patron in patrones_actual:
                for m in re.findall(patron, raw, re.IGNORECASE):
                    agregar_actual(m)

            for patron in patrones_tachado:
                for m in re.findall(patron, raw, re.IGNORECASE):
                    agregar_tachado(m)

    except:
        pass

    precios_actuales = sorted(set([p for p in precios_actuales if 10000 <= p <= 500000]))
    precios_tachados = sorted(set([p for p in precios_tachados if 10000 <= p <= 500000]))

    return precios_actuales, precios_tachados


def extraer_pdp_price_box(driver):
    """
    Prioriza el bloque real del PDP de Farmatodo.
    En tu HTML actual:
    - .price-box__current-price -> 107663
    - .price-box__original-price -> 143550
    """
    selectores_contenedor = [
        ".price-box",
        "app-pdp-price-box .price-box",
        ".price-box__price-section",
    ]

    selectores_actual = [
        ".price-box__current-price",
        ".price-box__price-container .price-box__current-price",
        ".price-box__price-container span:first-child",
    ]

    selectores_tachado = [
        ".price-box__original-price",
        ".price-box__price-container .price-box__original-price",
        ".price-box__price-container span:nth-child(2)",
    ]

    for sel_cont in selectores_contenedor:
        try:
            contenedores = driver.find_elements(By.CSS_SELECTOR, sel_cont)
        except:
            contenedores = []

        for cont in contenedores:
            try:
                texto_cont = obtener_texto_elemento(cont)
                if not texto_cont:
                    continue

                actuales = extraer_desde_selectores(driver, selectores_actual, contenedor=cont)
                tachados = extraer_desde_selectores(driver, selectores_tachado, contenedor=cont)

                precio_actual = min(actuales) if actuales else None
                precio_tachado = None

                if precio_actual and tachados:
                    mayores = [p for p in tachados if p > precio_actual]
                    if mayores:
                        precio_tachado = max(mayores)

                # fallback por texto del mismo bloque
                if precio_actual is None:
                    vals = extraer_valores_desde_texto(texto_cont)
                    if vals:
                        precio_actual = min(vals)

                if precio_actual:
                    return precio_actual, precio_tachado
            except:
                continue

    return None, None


def extraer_card_price_style(driver):
    """
    Fallback para estructuras tipo cards de Farmatodo:
    - .price__text-price
    - .price__text-offer-price
    Pero tratando de no contaminar con carruseles.
    """
    candidatos = []

    selectores_bloque = [
        ".price-box__price-container",
        ".price-box__price-section",
        ".price",
    ]

    for sel in selectores_bloque:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                txt = obtener_texto_elemento(e)
                if "$" not in txt:
                    continue
                candidatos.append((e, txt))
        except:
            pass

    mejor_actual = None
    mejor_tachado = None

    for elem, txt in candidatos:
        try:
            actuales = extraer_desde_selectores(
                driver,
                [
                    ".price__text-price",
                    ".price__full-price",
                    ".price-box__current-price",
                ],
                contenedor=elem
            )
            tachados = extraer_desde_selectores(
                driver,
                [
                    ".price__text-offer-price",
                    ".price-box__original-price",
                    "del",
                    "s",
                ],
                contenedor=elem
            )

            precio_actual = min(actuales) if actuales else None
            precio_tachado = None

            if precio_actual and tachados:
                mayores = [p for p in tachados if p > precio_actual]
                if mayores:
                    precio_tachado = max(mayores)

            if precio_actual:
                mejor_actual = precio_actual
                mejor_tachado = precio_tachado
                break
        except:
            continue

    return mejor_actual, mejor_tachado


def resolver_precios(precio_actual, precio_tachado):
    if precio_actual and precio_tachado and precio_tachado > precio_actual:
        return precio_tachado, precio_actual, "COP"

    if precio_actual:
        return precio_actual, None, "COP"

    return None, None, "COP"


def extraer_farmatodo(url, timeout=30, max_retries=3, driver=None, wait=None):
    if driver is None:
        raise Exception("Farmatodo requiere Selenium driver (no se pasó driver)")

    if wait is None:
        wait = WebDriverWait(driver, timeout)

    for intento in range(1, max_retries + 1):
        try:
            driver.get(url)
            time.sleep(random.uniform(3, 5))

            # ==========================================
            # 1) PRIORIDAD ABSOLUTA: BLOQUE PDP ACTUAL
            # ==========================================
            precio_actual, precio_tachado = extraer_pdp_price_box(driver)

            if precio_actual:
                return resolver_precios(precio_actual, precio_tachado)

            # ==========================================
            # 2) FALLBACK ESTRUCTURA DE PRECIOS TIPO CARD
            # ==========================================
            precio_actual, precio_tachado = extraer_card_price_style(driver)

            if precio_actual:
                return resolver_precios(precio_actual, precio_tachado)

            # ==========================================
            # 3) FALLBACK JSON / SCRIPTS
            # ==========================================
            json_actuales, json_tachados = extraer_precios_json(driver)

            precio_actual = min(json_actuales) if json_actuales else None
            precio_tachado = None

            if precio_actual and json_tachados:
                candidatos_tachado = [p for p in json_tachados if p > precio_actual]
                if candidatos_tachado:
                    precio_tachado = max(candidatos_tachado)

            if precio_actual:
                return resolver_precios(precio_actual, precio_tachado)

            raise Exception("No se encontraron precios válidos en Farmatodo")

        except Exception as e:
            print(f"❌ Farmatodo intento {intento} fallido: {e}")
            time.sleep(random.uniform(2, 4))

    return None, None, "COP"