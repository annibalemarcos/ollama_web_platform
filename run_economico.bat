@echo off
mode con: cols=68 lines=14
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo  Ollama Web Platform - Modo Economico
echo ===============================================
echo.

if not exist ".venv" (
  echo Ambiente virtual nao encontrado. Rodando install.bat...
  call install.bat
)

call .venv\Scripts\activate.bat

echo Rodando Flask em prioridade BAIXA.
echo Abrindo em: http://127.0.0.1:5388
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\positioned_server.ps1" -WindowTitle "Ollama Web Platform ECO" -CommandLine "python app.py" -Cols 68 -Lines 14 -InitialPositionDelaySeconds 12

pause
