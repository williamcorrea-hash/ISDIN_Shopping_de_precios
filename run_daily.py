import os
import sys
import time
import queue
import subprocess
import threading

import pandas as pd

from utils import normalizar_tienda
from config import TIENDAS_LENTAS


# ==================================
# AJUSTES DE PARALELISMO
# ==================================
# Puedes probar 3 en slow. Si notas que el PC se pone inestable,
# vuelve a 2.
TIENDAS_SLOW_MAX_PARALELO = 3
TIENDAS_FAST_MAX_PARALELO = 3


# ==================================
# INPUT
# ==================================
def get_input_file(base_dir: str) -> str:
    archivo_entrada = os.path.join(base_dir, "data", "productos.xlsx")
    if not os.path.exists(archivo_entrada):
        raise FileNotFoundError(f"No se encontro el archivo de entrada: {archivo_entrada}")
    return archivo_entrada


def extraer_tiendas_del_excel(base_dir: str):
    archivo = get_input_file(base_dir)
    df = pd.read_excel(archivo, sheet_name="Hoja1")

    if "Tienda" not in df.columns:
        raise ValueError("El archivo productos.xlsx no tiene columna 'Tienda'")

    tiendas = sorted(
        {
            normalizar_tienda(t)
            for t in df["Tienda"].dropna().astype(str).tolist()
            if str(t).strip()
        }
    )
    return tiendas


# ==================================
# EJECUCION DE CADA TIENDA
# ==================================
def ejecutar_tienda(tienda: str):
    inicio = time.time()
    cmd = [sys.executable, "main.py", tienda]

    print(f"Iniciando tienda: {tienda}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        duracion = round(time.time() - inicio, 2)

        return {
            "tienda": tienda,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duracion": duracion,
        }
    except Exception as e:
        duracion = round(time.time() - inicio, 2)
        return {
            "tienda": tienda,
            "returncode": 999,
            "stdout": "",
            "stderr": str(e),
            "duracion": duracion,
        }


def worker(cola_tareas, resultados, lock_resultados):
    while True:
        try:
            tienda = cola_tareas.get_nowait()
        except queue.Empty:
            return

        try:
            resultado = ejecutar_tienda(tienda)
            with lock_resultados:
                resultados.append(resultado)
        finally:
            cola_tareas.task_done()


def correr_grupo(tiendas, max_paralelo):
    if not tiendas:
        return []

    cola_tareas = queue.Queue()
    resultados = []
    lock_resultados = threading.Lock()

    for tienda in tiendas:
        cola_tareas.put(tienda)

    hilos = []
    total_hilos = min(max_paralelo, len(tiendas))

    for _ in range(total_hilos):
        t = threading.Thread(
            target=worker,
            args=(cola_tareas, resultados, lock_resultados),
            daemon=True
        )
        t.start()
        hilos.append(t)

    cola_tareas.join()

    for t in hilos:
        t.join(timeout=1)

    return resultados


def imprimir_resultados(resultados, titulo):
    print("\n" + "=" * 70)
    print(titulo)
    print("=" * 70)

    for r in sorted(resultados, key=lambda x: x["tienda"]):
        estado = "OK" if r["returncode"] == 0 else "ERROR"
        print(f"{r['tienda']:<15} | {estado:<5} | {r['duracion']} seg")

        if r["returncode"] != 0:
            print("---- STDOUT ----")
            print(r["stdout"][-3000:] if r["stdout"] else "")
            print("---- STDERR ----")
            print(r["stderr"][-3000:] if r["stderr"] else "")
            print("-" * 70)


# ==================================
# EJECUTAR FAST Y SLOW A LA VEZ
# ==================================
def correr_fast_y_slow_en_paralelo(tiendas_fast, tiendas_slow):
    resultados_fast = []
    resultados_slow = []

    def job_fast():
        nonlocal resultados_fast
        resultados_fast = correr_grupo(tiendas_fast, TIENDAS_FAST_MAX_PARALELO)

    def job_slow():
        nonlocal resultados_slow
        resultados_slow = correr_grupo(tiendas_slow, TIENDAS_SLOW_MAX_PARALELO)

    hilo_fast = threading.Thread(target=job_fast, daemon=True)
    hilo_slow = threading.Thread(target=job_slow, daemon=True)

    hilo_fast.start()
    hilo_slow.start()

    hilo_fast.join()
    hilo_slow.join()

    return resultados_fast, resultados_slow


# ==================================
# MAIN
# ==================================
def main():
    tiempo_inicio = time.time()
    base_dir = os.getcwd()

    print("=" * 70)
    print("INICIO RUN DIARIO")
    print("=" * 70)

    tiendas_excel = extraer_tiendas_del_excel(base_dir)
    tiendas_lentas_norm = {normalizar_tienda(t) for t in TIENDAS_LENTAS}

    tiendas_fast = [t for t in tiendas_excel if t not in tiendas_lentas_norm]
    tiendas_slow = [t for t in tiendas_excel if t in tiendas_lentas_norm]

    print(f"Tiendas detectadas: {tiendas_excel}")
    print(f"Fast: {tiendas_fast}")
    print(f"Slow: {tiendas_slow}")
    print(f"Paralelo fast: {TIENDAS_FAST_MAX_PARALELO}")
    print(f"Paralelo slow: {TIENDAS_SLOW_MAX_PARALELO}")

    resultados_fast, resultados_slow = correr_fast_y_slow_en_paralelo(
        tiendas_fast,
        tiendas_slow
    )

    resultados = resultados_fast + resultados_slow

    imprimir_resultados(resultados_fast, "RESULTADOS TIENDAS FAST")
    imprimir_resultados(resultados_slow, "RESULTADOS TIENDAS SLOW")

    print("\nEjecutando consolidacion final...")
    consolidar = subprocess.run(
        [sys.executable, "consolidar.py"],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )

    print("\n" + "=" * 70)
    print("CONSOLIDACION")
    print("=" * 70)
    if consolidar.stdout:
        print(consolidar.stdout)

    if consolidar.returncode != 0:
        print("Error en consolidacion:")
        if consolidar.stderr:
            print(consolidar.stderr)

    tiempo_total = time.time() - tiempo_inicio
    minutos = int(tiempo_total // 60)
    segundos = int(tiempo_total % 60)

    total_ok = sum(1 for r in resultados if r["returncode"] == 0)
    total_error = sum(1 for r in resultados if r["returncode"] != 0)

    print("\n" + "=" * 70)
    print("RESUMEN RUN DIARIO")
    print("=" * 70)
    print(f"Total tiendas ejecutadas: {len(resultados)}")
    print(f"Tiendas OK: {total_ok}")
    print(f"Tiendas con error: {total_error}")
    print(f"Tiempo total run_daily: {minutos} min {segundos} seg")
    print("=" * 70)


if __name__ == "__main__":
    main()