@echo off
title GeoVagas - Plataforma de Vagas por Localizacao
echo ========================================================
echo               INICIANDO O GEOVAGAS                      
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/2] Verificando dados e sincronizacao de vagas...
if not exist "data\vagas.json" (
    echo Baixando vagas da PBH e geolocalizando...
    python scraper.py
)

echo [2/2] Iniciando servidor web do GeoVagas...
echo.
echo O site abrira automaticamente no seu navegador padrao.
echo Para fechar o servidor, basta fechar esta janela ou pressionar Ctrl + C.
echo.

python server.py

pause
