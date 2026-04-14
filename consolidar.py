import os
import glob
from datetime import datetime

import pandas as pd


# ==================================
# AJUSTE
# ==================================
BORRAR_INTERMEDIOS_DESPUES_DE_CONSOLIDAR = True


# ==================================
# PATHS
# ==================================
def build_paths(base_dir: str):
    now = datetime.now()
    month_folder = now.strftime("%Y-%m")
    day_stamp = now.strftime("%Y-%m-%d")

    out_dir = os.path.join(base_dir, "output", month_folder)
    consolidado = os.path.join(out_dir, f"consolidado_{day_stamp}.xlsx")

    return out_dir, day_stamp, consolidado


# ==================================
# BUSCAR ARCHIVOS
# ==================================
def obtener_archivos_para_consolidar(out_dir: str, day_stamp: str, consolidado: str):
    patron = os.path.join(out_dir, f"precios_*_{day_stamp}_*.xlsx")
    archivos = sorted(glob.glob(patron))

    archivos = [
        a for a in archivos
        if os.path.basename(a).lower() != os.path.basename(consolidado).lower()
    ]

    return archivos


# ==================================
# CONSOLIDAR
# ==================================
def consolidar_archivos(archivos, consolidado):
    frames = []

    print("Archivos encontrados para consolidar:")
    for a in archivos:
        print(f" - {a}")

    for archivo in archivos:
        try:
            df = pd.read_excel(archivo)
            df["archivo_origen"] = os.path.basename(archivo)
            frames.append(df)
        except Exception as e:
            print(f"WARNING: No se pudo leer {archivo}: {e}")

    if not frames:
        raise Exception("No se pudieron leer archivos validos para consolidar.")

    df_final = pd.concat(frames, ignore_index=True)

    if "Producto" in df_final.columns and "Tienda" in df_final.columns and "fecha_busqueda" in df_final.columns:
        df_final = df_final.drop_duplicates(
            subset=["Producto", "Tienda", "fecha_busqueda"],
            keep="last"
        )

    df_final.to_excel(consolidado, index=False)

    return df_final


# ==================================
# BORRAR INTERMEDIOS
# ==================================
def borrar_archivos_intermedios(archivos):
    eliminados = []
    errores = []

    for archivo in archivos:
        try:
            if os.path.exists(archivo):
                os.remove(archivo)
                eliminados.append(archivo)
        except Exception as e:
            errores.append((archivo, str(e)))

    return eliminados, errores


# ==================================
# MAIN
# ==================================
def main():
    base_dir = os.getcwd()
    out_dir, day_stamp, consolidado = build_paths(base_dir)

    if not os.path.exists(out_dir):
        raise FileNotFoundError(f"No existe la carpeta de salida: {out_dir}")

    archivos = obtener_archivos_para_consolidar(out_dir, day_stamp, consolidado)

    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron archivos para consolidar con patron: "
            f"{os.path.join(out_dir, f'precios_*_{day_stamp}_*.xlsx')}"
        )

    df_final = consolidar_archivos(archivos, consolidado)

    print("\nConsolidado generado:")
    print(consolidado)
    print(f"Total filas consolidadas: {len(df_final)}")

    if BORRAR_INTERMEDIOS_DESPUES_DE_CONSOLIDAR:
        eliminados, errores = borrar_archivos_intermedios(archivos)

        print("\nLimpieza de archivos intermedios:")
        print(f"Eliminados: {len(eliminados)}")

        if errores:
            print(f"Con error al eliminar: {len(errores)}")
            for archivo, error in errores:
                print(f" - {archivo} -> {error}")
        else:
            print("Todos los archivos intermedios fueron eliminados correctamente.")


if __name__ == "__main__":
    main()