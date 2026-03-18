import json
import re
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def normalizar_precio_json(valor):
    """
    Algunos JSON pueden traer COP como:
    120700
    o en algunos casos 12070000
    """
    if valor is None:
        return None

    try:
        if isinstance(valor, str):
            valor = re.sub(r"[^\d]", "", valor)
            if not valor:
                return None
            valor = int(valor)
        elif isinstance(valor, float):
            valor = int(round(valor))
        elif isinstance(valor, int):
            pass
        else:
            return None

        # Ajuste por si viene inflado en 100x
        if valor > 9_999_999:
            valor = int(round(valor / 100))

        return valor
    except Exception:
        return None


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


def crear_sesion():
    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })

    return session


def get_html(url, timeout=30):
    """
    verify=False para evitar error SSL corporativo:
    self-signed certificate in certificate chain
    """
    session = crear_sesion()
    response = session.get(url, timeout=timeout, verify=False)
    response.raise_for_status()
    return response.text


def extraer_json_ld_y_next_data(html):
    bloques = []

    for bloque in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            bloques.append(json.loads(bloque.strip()))
        except Exception:
            pass

    for bloque in re.findall(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            bloques.append(json.loads(bloque.strip()))
        except Exception:
            pass

    return bloques


def buscar_valores_precio_en_json(obj):
    encontrados = []

    claves_precio = {
        "price",
        "pricenow",
        "bestprice",
        "specialprice",
        "saleprice",
        "offerprice",
        "internetprice",
        "normalprice",
        "listprice",
        "sale_price",
        "regular_price",
        "special_price",
        "lowprice",
        "highprice",
        "sellingprice",
        "priceamount",
        "compare_at_price",
        "compareatprice",
        "compareprice",
    }

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                lk = str(k).lower()

                if lk in claves_precio:
                    valor = normalizar_precio_json(v)
                    if valor:
                        encontrados.append((lk, valor))

                walk(v)

        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)
    return encontrados


def resolver_precios_desde_json(candidatos):
    normal = None
    oferta = None

    for data in candidatos:
        hallazgos = buscar_valores_precio_en_json(data)

        for k, v in hallazgos:
            if any(x in k for x in ["sale", "special", "best", "offer", "selling", "low"]):
                oferta = oferta or v

        for k, v in hallazgos:
            if any(x in k for x in ["regular", "normal", "list", "high", "compare"]):
                normal = normal or v

        if oferta is None:
            for k, v in hallazgos:
                if k == "price" or "price" in k:
                    oferta = v
                    break

        if normal is None and oferta is not None:
            normal = oferta

        if normal is not None:
            if oferta == normal:
                oferta = None
            elif oferta is not None and oferta > normal:
                normal, oferta = oferta, normal
            return normal, oferta

    return None, None


def extraer_precios_desde_texto(texto):
    matches = re.findall(r'\$\s*[\d\.\,]+', texto)
    valores = [limpiar_precio(x) for x in matches if limpiar_precio(x)]
    valores = [v for v in valores if v is not None]
    valores = sorted(set(valores))

    if not valores:
        return None, None

    if len(valores) == 1:
        return valores[0], None

    return max(valores), min(valores)


def extraer_precios_de_bloque_texto(texto):
    """
    Toma un bloque concreto de texto del precio y devuelve:
    normal = mayor
    oferta = menor
    """
    matches = re.findall(r'\$\s*[\d\.\,]+', texto)
    valores = [limpiar_precio(x) for x in matches if limpiar_precio(x)]
    valores = [v for v in valores if v is not None]

    if not valores:
        return None, None

    # conservar únicos pero sin perder mucho el contexto
    unicos = []
    for v in valores:
        if v not in unicos:
            unicos.append(v)

    if len(unicos) == 1:
        return unicos[0], None

    normal = max(unicos)
    oferta = min(unicos)

    if normal == oferta:
        oferta = None

    return normal, oferta