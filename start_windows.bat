@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto run
where py >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.11 ou superior e execute este arquivo novamente.
  pause
  exit /b 1
)
py -3 -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 ou superior necessario'"
if errorlevel 1 goto fail
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
:run
.venv\Scripts\python.exe -m app
if errorlevel 1 goto fail
exit /b 0
:fail
echo Falha ao iniciar. Consulte a mensagem acima e output\app.log.
pause
exit /b 1
