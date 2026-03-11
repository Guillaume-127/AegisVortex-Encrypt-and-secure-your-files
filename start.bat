@echo off
title Verrouilleur de Fichiers
color 0A

:: Verifie si Python est installe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    pause
    exit /b
)

:: Verification et creation de l'environnement virtuel (venv)
if exist "venv\Scripts\activate.bat" goto venv_exists

echo [INFO] Creation de l'environnement virtuel Python...
python -m venv venv

echo [INFO] Installation des dependances de securite...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
python -m pip install cryptography --quiet
goto launch

:venv_exists
call venv\Scripts\activate.bat

:launch
:: Lance le script Python
echo Lancement de l'interface de securite...
python secu_files.py

:: Desactivation de l'environnement virtuel en quittant
call deactivate
pause
