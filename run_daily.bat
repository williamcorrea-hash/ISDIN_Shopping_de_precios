@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM  RUN DAILY - Shopping de precios
REM  - Ejecuta main.py usando la venv del proyecto
REM  - Crea logs diarios y mantiene un run_test.log
REM ==========================================================

REM 1) Trabajar SIEMPRE en la carpeta donde está este .bat
set "HERE=%~dp0"
cd /d "%HERE%"

REM 2) Asegurar carpetas
if not exist "%HERE%logs" mkdir "%HERE%logs"
if not exist "%HERE%output" mkdir "%HERE%output"

REM 3) Fecha YYYY-MM-DD (robusto en Windows con WMIC)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "dt=%%I"
set "YYYY=!dt:~0,4!"
set "MM=!dt:~4,2!"
set "DD=!dt:~6,2!"
set "TODAY=!YYYY!-!MM!-!DD!"

REM 4) Archivos log
set "LOG_DAILY=%HERE%logs\run_!TODAY!.log"
set "LOG_LAST=%HERE%logs\run_test.log"

REM 5) Encabezado del log
echo =========================================================>> "!LOG_DAILY!"
echo RUN !TODAY!  %date% %time%>> "!LOG_DAILY!"
echo PROYECTO: %HERE%>> "!LOG_DAILY!"
echo =========================================================>> "!LOG_DAILY!"

REM 6) Ejecutar Python (venv)
set "PYTHON_EXE=%HERE%.venv\Scripts\python.exe"
set "MAIN_PY=%HERE%main.py"

if not exist "!PYTHON_EXE!" (
  echo ERROR: No existe python de venv en: !PYTHON_EXE!>> "!LOG_DAILY!"
  echo Revisa que exista .venv\Scripts\python.exe>> "!LOG_DAILY!"
  copy /y "!LOG_DAILY!" "!LOG_LAST!" >nul
  exit /b 1
)

if not exist "!MAIN_PY!" (
  echo ERROR: No existe main.py en: !MAIN_PY!>> "!LOG_DAILY!"
  copy /y "!LOG_DAILY!" "!LOG_LAST!" >nul
  exit /b 1
)

REM 7) Ejecutar y guardar salida + errores
"!PYTHON_EXE!" "!MAIN_PY!" >> "!LOG_DAILY!" 2>&1

REM 8) Guardar copia del último log
copy /y "!LOG_DAILY!" "!LOG_LAST!" >nul

REM 9) Código de salida
set "ERR=%ERRORLEVEL%"
echo.>> "!LOG_DAILY!"
echo FIN %date% %time% - EXITCODE=!ERR!>> "!LOG_DAILY!"
exit /b !ERR!
