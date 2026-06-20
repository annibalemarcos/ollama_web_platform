@echo off
mode con: cols=68 lines=14
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo  Ollama Web Platform - Instalador Windows
echo ===============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  echo Instale Python 3.11+ e marque a opcao "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv" (
  echo [1/3] Criando ambiente virtual...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/3] Atualizando pip...
python -m pip install --upgrade pip

echo [3/3] Instalando dependencias...
pip install -r requirements.txt

echo.
echo Instalacao concluida.
echo Agora execute run.bat
echo.
pause
