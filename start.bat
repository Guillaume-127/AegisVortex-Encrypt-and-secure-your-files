@echo off
:: Passage en UTF-8 pour les accents
chcp 65001 >nul
title AEGIS-VORTEX V3.8 - MATRI-X EDITION
color 0A

:: LOGO ROBUSTE AEGIS-VORTEX
echo.
echo   __________________________________________________________________________
echo  ^|                                                                          ^|
echo  ^|   AEGIS-VORTEX V3.8 [ TURBO ENGINE ]                                   ^|
echo  ^|   DEFENSE GRID : ACTIVE                                                ^|
echo  ^|^|________________________________________________________________________^|^|
echo.

:: Vérification Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas detecte sur votre systeme.
    pause
    exit /b
)

:: Gestion de l'environnement virtuel
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Premier lancement : Creation de l'environnement virtuel...
    python -m venv venv
)

call venv\Scripts\activate.bat

:: Installation des dependances
echo [INFO] Verification des dependances (AegisVortex Module)...
python -m pip install --upgrade pip --quiet
if exist "requirements.txt" (
    python -m pip install -r requirements.txt --quiet
) else (
    python -m pip install cryptography zstandard argon2-cffi tqdm customtkinter darkdetect windnd --quiet
)

cls
echo.
echo  ====================================================================
echo    AEGIS-VORTEX V3.8 - MATRI-X STABILITY READY
echo  ====================================================================
echo.
echo   [1] Interface Graphique (Recommande)
echo   [2] Console (Expert)
echo.

set /p c=" [ CHOICE ] : "

if "%c%"=="2" (
    python secu_files.py
) else (
    python gui.py
)

call deactivate
pause
