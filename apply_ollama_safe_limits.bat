@echo off
mode con: cols=68 lines=14
setlocal

echo.
echo ===============================================
echo  Ollama - limites seguros para PC fraco/medio
echo ===============================================
echo.

echo Aplicando variaveis de ambiente do usuario...
setx OLLAMA_NUM_PARALLEL 1 >nul
setx OLLAMA_MAX_LOADED_MODELS 1 >nul
setx OLLAMA_MAX_QUEUE 1 >nul
setx OLLAMA_KEEP_ALIVE 0 >nul
setx OLLAMA_FLASH_ATTENTION 1 >nul
setx OLLAMA_KV_CACHE_TYPE q8_0 >nul

echo.
echo Feito.
echo.
echo IMPORTANTE:
echo 1. Feche o Ollama pelo icone perto do relogio do Windows.
echo 2. Abra o Ollama de novo.
echo 3. Rode o app normalmente.
echo.
echo Se algo ficar estranho, remova essas variaveis em:
echo Sistema ^> Configuracoes Avancadas ^> Variaveis de Ambiente
echo.
pause
