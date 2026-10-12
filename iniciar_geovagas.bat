@echo off
setlocal
title GeoVagas - LinkedIn, Indeed, Glassdoor e GOBH
echo ========================================================
echo            INICIANDO A NOVA VERSAO DO GEOVAGAS
echo ========================================================
echo.
cd /d "%~dp0"

echo Verificando Python 3.10 ou superior...
set "PYTHON_CMD=py -3"
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 goto python_ready
set "PYTHON_CMD=python"
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 goto python_error

:python_ready
echo Python compativel encontrado.
if exist ".venv\Scripts\python.exe" goto use_venv

echo Criando ambiente virtual local...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 goto venv_error

:use_venv
set "PYTHON_CMD=%CD%\.venv\Scripts\python.exe"
"%PYTHON_CMD%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 goto venv_version_error

echo.
echo Conferindo a dependencia JobSpy...
"%PYTHON_CMD%" -c "from importlib.metadata import version; raise SystemExit(0 if version('python-jobspy') == '1.3.0' else 1)" >nul 2>&1
if not errorlevel 1 goto start_server

echo Instalando as dependencias definidas em requirements.txt...
"%PYTHON_CMD%" -m pip install -r requirements.txt
if errorlevel 1 goto dependency_error

:start_server
echo.
echo Iniciando servidor web do GeoVagas...
echo O site abrira automaticamente no seu navegador padrao.
echo Para fechar o servidor, pressione Ctrl + C.
echo.
"%PYTHON_CMD%" server.py
goto finish

:python_error
echo ERRO: Instale Python 3.10 ou superior e habilite o comando py ou python.
goto finish

:venv_error
echo ERRO: Nao foi possivel criar o ambiente virtual Python do projeto.
goto finish

:venv_version_error
echo ERRO: O ambiente .venv existente usa Python anterior ao 3.10.
echo Remova a pasta .venv e execute este arquivo novamente.
goto finish

:dependency_error
echo ERRO: Nao foi possivel instalar o JobSpy. Verifique sua conexao com a internet e tente novamente.

:finish
pause
endlocal
