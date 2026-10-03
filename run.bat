@echo off
rem ====================================================================
rem  Gestion Articles (web) - demarrage local, hors-ligne
rem  Dependance : Python 3.10 a 3.14 (https://www.python.org/downloads/)
rem  Les paquets sont installes depuis le dossier wheels\ sans internet ;
rem  a defaut, pip est appele en ligne.
rem ====================================================================
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

rem ---------------------------------------------------------- Python
set "PY="
call :try_python "C:\Python314\python.exe"
if not defined PY for /f "delims=" %%I in ('where python 2^>nul') do if not defined PY call :try_python "%%I"
if not defined PY for /f "delims=" %%I in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do if not defined PY call :try_python "%%I"
if not defined PY goto python_manquant
echo [1/4] Python : %PY%

rem ------------------------------------------------------ dependances
"%PY%" -c "import flask, openpyxl, reportlab" >nul 2>nul
if not errorlevel 1 goto deps_ok
echo [2/4] Installation des dependances...
if not exist "wheels\" goto deps_en_ligne
echo       Paquets locaux du dossier wheels, sans internet.
"%PY%" -m pip install --no-index --find-links wheels -r requirements.txt --disable-pip-version-check
if not errorlevel 1 goto deps_ok
echo       Dossier wheels incompatible avec cette version de Python.
echo       Nouvelle tentative via internet.

:deps_en_ligne
"%PY%" -m pip --version >nul 2>nul
if not errorlevel 1 goto deps_pip_ok
"%PY%" -m ensurepip --default-pip >nul 2>nul
"%PY%" -m pip --version >nul 2>nul
if errorlevel 1 goto deps_erreur
:deps_pip_ok
"%PY%" -m pip install -r requirements.txt --disable-pip-version-check
if not errorlevel 1 goto deps_ok

:deps_erreur
echo [ERREUR] Installation des dependances impossible.
echo   - hors-ligne : wheels ne contient pas de paquet pour ce Python
echo   - en ligne   : verifiez la connexion internet puis relancez run.bat
pause
exit /b 1

:deps_ok
echo [2/4] Dependances pretes.

rem ------------------------------------------------------ base de donnees
set "FIRST=0"
if not exist "web_app.db" set "FIRST=1"
if not exist ".session.key" set "FIRST=1"
if "%FIRST%"=="1" (
  echo [3/4] Premiere execution : initialisation de la base...
  "%PY%" -m flask --app app init-db
  "%PY%" -m flask --app app import-seed
) else (
  echo [3/4] Base prete.
)

rem ---------------------------------------------------------- serveur
echo [4/4] Demarrage : le navigateur s'ouvre automatiquement.
"%PY%" serve.py --open %*
if errorlevel 1 (
  echo.
  echo [ERREUR] Le serveur s'est arrete avec une erreur - voir ci-dessus.
  echo Si le port 8765 est bloque, fermez l'application qui l'utilise.
  pause
)
endlocal
exit /b 0

rem ================================================ sous-routines =====
:try_python
if "%~1"=="" goto :eof
if not exist "%~1" goto :eof
"%~1" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto :eof
set "PY=%~1"
goto :eof

:python_manquant
echo [ERREUR] Python 3.10 a 3.14 introuvable sur cette machine.
echo Telechargez-le sur https://www.python.org/downloads/
echo Cochez l'option "Add Python to PATH" pendant l'installation, puis relancez run.bat.
pause
exit /b 1
