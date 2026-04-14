import os
import sys
import time
import random
from datetime import datetime

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from validators import precio_valido
from config import TIENDAS_LENTAS, max_workers_requests
from utils import normalizar_tienda

from extractors.medipiel import extraer_medipiel
from extractors.farmatodo import extraer_farmatodo
from extractors.cruz_verde import extraer_cruz_verde
from extractors.cutis import extraer_cutis
from extractors.bellapiel import extraer_bellapiel
from extractors.linea_estetica import extraer_linea_estetica
from extractors.falabella import extraer_falabella
from extractors.laskin import extraer_laskin
from extractors.pasteur import extraer_pasteur


# ==================================
# EXTRACTORES
# ==================================
EXTRACTORES = {
    "medipiel": extraer_medipiel,
    "farmatodo": extraer_farmatodo,
    "cruzverde": extraer_cruz_verde,
    "cutis": extraer_cutis,
    "bellapiel": extraer_bellapiel,
    "lineaestetica": extraer_linea_estetica,
    "falabella": extraer_falabella,
    "laskin": extraer_laskin,
    "pasteur": extraer_pasteur,
}

TIENDAS_SOPORTADAS = set(EXTRACTORES.keys())


# ==================================
# INPUT
# ==================================
def get_input_file(base_dir: str) -> str:
    archivo_entrada = os.path.join(base_dir, "data", "productos.xlsx")
    if not os.path.exists(archivo_entrada):
        raise FileNotFoundError(f"No se encontro el archivo de entrada: {archivo_entrada}")
    return archivo_entrada


# ==================================
# OUTPUT PATHS
# ==================================
def build_output_paths(base_dir: str, now: datetime, etiqueta: str):
    month_folder = now.strftime("%Y-%m")
    day_stamp = now.strftime("%Y-%m-%d")
    time_stamp = now.strftime("%H-%M-%S")

    out_dir = os.path.join(base_dir, "output", month_folder)
    os.makedirs(out_dir, exist_ok=True)

    nombre = f"precios_{etiqueta}_{day_stamp}_{time_stamp}.xlsx"
    out_file = os.path.join(out_dir, nombre)

    return out_dir, out_file


# ==================================
# OBTENER PRECIO
# ==================================
def obtener_precio(tienda, url, driver=None, wait=None):
    try:
        extractor = EXTRACTORES[tienda]

        if driver is not None:
            precio_normal, precio_oferta, moneda = extractor(url, driver=driver, wait=wait)
        else:
            precio_normal, precio_oferta, moneda = extractor(url)

        time.sleep(random.uniform(1.0, 2.0))

        if precio_valido(precio_normal):
            return precio_normal, precio_oferta, moneda, "OK"

        return None, None, None, "PRECIO_INVALIDO"

    except Exception as e:
        return None, None, None, f"ERROR: {str(e)}"


# ==================================
# SELENIUM DRIVER EDGE
# ==================================
def iniciar_driver_edge():
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service as EdgeService

    options = EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-features=msEdgeSignin")

    temp_profile = os.path.join(
        os.getcwd(),
        "edge_profile_tmp",
        f"session_{int(time.time())}_{random.randint(1000,9999)}"
    )
    os.makedirs(temp_profile, exist_ok=True)
    options.add_argument(f"--user-data-dir={temp_profile}")

    drivers_path = os.path.join(os.getcwd(), "drivers", "msedgedriver.exe")
    if os.path.exists(drivers_path):
        service = EdgeService(executable_path=drivers_path)
        driver = webdriver.Edge(service=service, options=options)
    else:
        driver = webdriver.Edge(options=options)

    return driver


# ==================================
# PROCESAR TIENDAS SLOW
# ==================================
def procesar_slow(df_slow):
    resultados = []

    if df_slow.empty:
        return resultados

    from selenium.webdriver.support.ui import WebDriverWait

    def new_driver():
        driver_local = iniciar_driver_edge()
        wait_local = WebDriverWait(driver_local, 30)
        return driver_local, wait_local

    try:
        driver, wait = new_driver()
    except Exception as e:
        print(f"WARNING: No se pudo iniciar Selenium/Edge. Se omiten registros slow. Error: {e}")
        return resultados

    try:
        for _, row in df_slow.iterrows():
            print(f"Procesando (selenium): {row.Producto} | {row.Tienda_raw}")

            precio_normal, precio_oferta, moneda, estado = obtener_precio(
                row.Tienda, row.URL, driver=driver, wait=wait
            )

            if isinstance(estado, str) and "invalid session id" in estado.lower():
                try:
                    try:
                        driver.quit()
                    except Exception:
                        pass

                    driver, wait = new_driver()
                    precio_normal, precio_oferta, moneda, estado = obtener_precio(
                        row.Tienda, row.URL, driver=driver, wait=wait
                    )
                except Exception as e:
                    precio_normal, precio_oferta, moneda, estado = None, None, None, f"ERROR: {str(e)}"

            resultados.append({
                "Producto": row.Producto,
                "Tienda": row.Tienda_raw,
                "Marca": row.Marca,
                "Precio Normal": precio_normal,
                "Precio Oferta": precio_oferta,
                "Moneda": moneda,
                "Estado": estado,
            })

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return resultados


# ==================================
# CARGAR Y FILTRAR
# ==================================
def cargar_datos(base_dir: str, tienda_objetivo: str | None):
    archivo_entrada = get_input_file(base_dir)
    df = pd.read_excel(archivo_entrada, sheet_name="Hoja1")

    print(f"Leyendo productos: {len(df)} encontrados")

    df["Tienda_raw"] = df["Tienda"]
    df["Tienda"] = df["Tienda"].apply(normalizar_tienda)

    if tienda_objetivo:
        tienda_norm = normalizar_tienda(tienda_objetivo)
        df = df[df["Tienda"] == tienda_norm].copy()
        print(f"Filtro por tienda '{tienda_objetivo}': {len(df)} registros")

        if df.empty:
            raise ValueError(f"No se encontraron registros para la tienda: {tienda_objetivo}")

    tiendas_invalidas = set(df["Tienda"]) - TIENDAS_SOPORTADAS
    if tiendas_invalidas:
        raise ValueError(f"Tiendas no soportadas: {tiendas_invalidas}")

    return df


# ==================================
# MAIN
# ==================================
def main():
    tiempo_inicio = time.time()

    tienda_objetivo = sys.argv[1].strip() if len(sys.argv) > 1 else None

    base_dir = os.getcwd()
    now = datetime.now()
    fecha_ejecucion = now.strftime("%Y-%m-%d %H:%M:%S")

    df = cargar_datos(base_dir, tienda_objetivo)

    tiendas_lentas_norm = {normalizar_tienda(t) for t in TIENDAS_LENTAS}

    df_fast = df[~df["Tienda"].isin(tiendas_lentas_norm)].copy()
    df_slow = df[df["Tienda"].isin(tiendas_lentas_norm)].copy()

    print(f"Registros fast: {len(df_fast)}")
    print(f"Registros slow: {len(df_slow)}")

    resultados = []

    # FAST
    if not df_fast.empty:
        with ThreadPoolExecutor(max_workers=max_workers_requests) as executor:
            futures = {}

            for _, row in df_fast.iterrows():
                print(f"Procesando (requests): {row.Producto} | {row.Tienda_raw}")
                future = executor.submit(obtener_precio, row.Tienda, row.URL)
                futures[future] = row

            for future in as_completed(futures):
                row = futures[future]
                precio_normal, precio_oferta, moneda, estado = future.result()

                resultados.append({
                    "Producto": row.Producto,
                    "Tienda": row.Tienda_raw,
                    "Marca": row.Marca,
                    "Precio Normal": precio_normal,
                    "Precio Oferta": precio_oferta,
                    "Moneda": moneda,
                    "Estado": estado,
                    "fecha_busqueda": fecha_ejecucion,
                })

    # SLOW
    try:
        resultados_slow = procesar_slow(df_slow)
    except Exception as e:
        print(f"WARNING: Selenium/slow fallo, se continuara sin slow. Error: {e}")
        resultados_slow = []

    for r in resultados_slow:
        r["fecha_busqueda"] = fecha_ejecucion
    resultados.extend(resultados_slow)

    # OUTPUT
    etiqueta = normalizar_tienda(tienda_objetivo) if tienda_objetivo else "todas"
    _, output_file = build_output_paths(base_dir, now, etiqueta)
    df_out = pd.DataFrame(resultados)

    try:
        df_out.to_excel(output_file, index=False)
        print(f"Archivo guardado en: {output_file}")
    except PermissionError:
        alt_output = output_file.replace(".xlsx", "_v2.xlsx")
        df_out.to_excel(alt_output, index=False)
        print(f"El archivo estaba abierto. Guardado alterno en: {alt_output}")
        output_file = alt_output

    # RESUMEN
    tiempo_total = time.time() - tiempo_inicio
    minutos = int(tiempo_total // 60)
    segundos = int(tiempo_total % 60)

    total_ok = (df_out["Estado"] == "OK").sum() if not df_out.empty else 0
    total_error = df_out["Estado"].astype(str).str.startswith("ERROR").sum() if not df_out.empty else 0
    total_precio_invalido = (df_out["Estado"] == "PRECIO_INVALIDO").sum() if not df_out.empty else 0

    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print(f"Tienda procesada: {tienda_objetivo if tienda_objetivo else 'TODAS'}")
    print(f"Total registros procesados: {len(df_out)}")
    print(f"OK: {total_ok}")
    print(f"ERROR: {total_error}")
    print(f"PRECIO_INVALIDO: {total_precio_invalido}")
    print(f"Tiempo total de ejecucion: {minutos} min {segundos} seg")
    print(f"Archivo final: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()