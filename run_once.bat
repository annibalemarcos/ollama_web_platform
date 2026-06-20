@echo off
mode con: cols=68 lines=14
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo  Ollama Web Platform - RUN ONCE
echo ===============================================
echo.
echo Este arquivo faz tudo em uma passada:
echo  1. instala/cria o ambiente Python
echo  2. aplica limites seguros do Ollama
echo  3. roda o app em modo economico
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  echo Instale Python 3.11+ e marque "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo [AVISO] Ollama nao foi encontrado no PATH.
  echo O app ainda pode abrir, mas o dropdown/modelos podem falhar.
  echo Instale pelo site oficial se ainda nao instalou.
  echo.
)

if not exist ".venv" (
  echo [1/5] Criando ambiente virtual...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERRO] Falha ao criar ambiente virtual.
    pause
    exit /b 1
  )
) else (
  echo [1/5] Ambiente virtual ja existe.
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [ERRO] Nao consegui ativar o ambiente virtual.
  pause
  exit /b 1
)

echo [2/5] Atualizando pip...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo [AVISO] Nao consegui atualizar o pip, tentando continuar...
)

echo [3/5] Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias.
  pause
  exit /b 1
)

echo [4/5] Aplicando limites seguros do Ollama...
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_MAX_QUEUE=1
set OLLAMA_KEEP_ALIVE=0
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_KV_CACHE_TYPE=q8_0

setx OLLAMA_NUM_PARALLEL 1 >nul
setx OLLAMA_MAX_LOADED_MODELS 1 >nul
setx OLLAMA_MAX_QUEUE 1 >nul
setx OLLAMA_KEEP_ALIVE 0 >nul
setx OLLAMA_FLASH_ATTENTION 1 >nul
setx OLLAMA_KV_CACHE_TYPE q8_0 >nul

echo.
echo Limites aplicados no Windows.
echo Se o Ollama ja estava aberto, feche pelo icone perto do relogio
echo e abra novamente depois para ele pegar tudo 100%%.
echo.

echo [5/5] Rodando Flask em prioridade baixa...
echo.
echo Abra no navegador:
echo http://127.0.0.1:5388
echo.
echo Para encerrar, feche a janela do servidor ou use CTRL+C.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\positioned_server.ps1" -WindowTitle "Ollama Web Platform ECO" -CommandLine "python app.py" -Cols 68 -Lines 14 -InitialPositionDelaySeconds 12

echo.
echo App encerrado.
echo.
pause
