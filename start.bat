@echo off
title AEGIS-VORTEX V3.8 - MATRI-X EDITION
color 0A

echo.
echo  --- AEGIS-VORTEX V3.8 [ TURBO ENGINE ] ---
echo  --- DEFENSE GRID : ACTIVE               ---
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'a pas ete detecte.
    pause
    exit /b
)

if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Premier lancement : Creation de l'environnement virtuel...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo [INFO] Mise a jour des dependances...
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