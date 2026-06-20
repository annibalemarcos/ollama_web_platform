@echo off
mode con: cols=68 lines=14
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo  Ollama Web Platform
echo ===============================================
echo.

if not exist ".venv" (
  echo Ambiente virtual nao encontrado. Rodando install.bat...
  call install.bat
)

call .venv\Scripts\activate.bat

echo Verificando modelo recomendado...
echo Se ainda nao baixou, rode em outro PowerShell: ollama pull gemma3:4b
echo.
echo Abrindo em: http://127.0.0.1:5388
echo.
python app.py

pause
