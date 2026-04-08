@echo off
title AEGIS-VORTEX V3.8 - MATRI-X EDITION
color 0A
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python absent.
    pause
    exit /b
)
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Création venv...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [INFO] MàJ dépendances...
python -m pip install --upgrade pip --quiet
python -m pip install cryptography zstandard argon2-cffi tqdm customtkinter darkdetect windnd --quiet
cls
echo 1. Interface Graphique (Recommandé)
echo 2. Console (Expert)
set /p c="Choix [1] : "
if "%c%"=="2" (
    python secu_files.py
) else (
    python gui.py
)
call deactivate
pause
