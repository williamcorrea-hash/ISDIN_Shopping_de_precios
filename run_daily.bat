@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "HERE=%~dp0"
cd /d "%HERE%"

if not exist "%HERE%logs" mkdir "%HERE%logs"
if not exist "%HERE%output" mkdir "%HERE%output"

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "dt=%%I"
set "YYYY=!dt:~0,4!"
set "MM=!dt:~4,2!"
set "DD=!dt:~6,2!"
set "TODAY=!YYYY!-!MM!-!DD!"

set "LOG_DAILY=%HERE%logs\run_!TODAY!.log"
set "LOG_LAST=%HERE%logs\run_test.log"

echo =========================================================>> "!LOG_DAILY!"
echo RUN !TODAY!  %date% %time%>> "!LOG_DAILY!"
echo PROYECTO: %HERE%>> "!LOG_DAILY!"
echo =========================================================>> "!LOG_DAILY!"

set "PYTHON_EXE=%HERE%.venv\Scripts\python.exe"
set "RUN_PY=%HERE%run_daily.py"

if not exist "!PYTHON_EXE!" (
  echo ERROR: No existe python de venv en: !PYTHON_EXE!>> "!LOG_DAILY!"
  copy /y "!LOG_DAILY!" "!LOG_LAST!" >nul
  exit /b 1
)

if not exist "!RUN_PY!" (
  echo ERROR: No existe run_daily.py en: !RUN_PY!>> "!LOG_DAILY!"
  copy /y "!LOG_DAILY!" "!LOG_LAST!" >nul
  exit /b 1
)

"!PYTHON_EXE!" "!RUN_PY!" >> "!LOG_DAILY!" 2>&1

copy /y "!LOG_DAILY!" "!LOG_LAST!" >nul

set "ERR=%ERRORLEVEL%"
echo.>> "!LOG_DAILY!"
echo FIN %date% %time% - EXITCODE=!ERR!>> "!LOG_DAILY!"
exit /b !ERR!