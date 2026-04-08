@echo off
title 🔒 SECU-FILES V2 - Console de Sécurisation
color 0A

:: Verifie si Python est installe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Veuillez installer Python depuis https://www.python.org/
    pause
    exit /b
)

:: Gestion de l'environnement virtuel
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Premier lancement : Creation de l'environnement virtuel...
    python -m venv venv
)

call venv\Scripts\activate.bat

:: Installation/Mise a jour des dependances V2
echo [INFO] Verification des modules de securite (V2)...
python -m pip install --upgrade pip --quiet
python -m pip install cryptography zstandard argon2-cffi tqdm --quiet

:: Lancement
cls
echo ========================================================
echo   LANCEMENT DE L'INTERFACE SECU-FILES V2 (PRO)
echo ========================================================
python secu_files.py

call deactivate
pause
