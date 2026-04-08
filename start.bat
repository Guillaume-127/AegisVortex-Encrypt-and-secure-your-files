@echo off
chcp 65001 >nul
title AEGIS-VORTEX V3.8 - MATRI-X EDITION
color 0A

:: LOGO ASCII AEGIS-VORTEX
echo.
echo  █████╗ ███████╗ ██████╗ ██╗███████╗    ██╗   ██╗ ██████╗ ██████╗ ████████╗███████╗██╗  ██╗
echo ██╔══██╗██╔════╝██╔════╝ ██║██╔════╝    ██║   ██║██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝
echo ███████║█████╗  ██║  ███╗██║███████╗    ██║   ██║██║   ██║██████╔╝   ██║   █████╗   ╚███╔╝ 
echo ██╔══██║██╔══╝  ██║   ██║██║╚════██║    ╚██╗ ██╔╝██║   ██║██╔══██╗   ██║   ██╔══╝   ██╔██╗ 
echo ██║  ██║███████╗╚██████╔╝██║███████║     ╚████╔╝ ╚██████╔╝██║  ██║   ██║   ███████╗██╔╝ ██╗
echo ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝╚══════╝      ╚═══╝   ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
echo.
echo ==============================================================================================
echo [ SISTEM ] : AEGIS-VORTEX V3.8 - MATRI-X STABILITY READY
echo [ STATUS ] : DEFENSE GRID ACTIVE
echo ==============================================================================================
echo.

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
python -m pip install -r requirements.txt --quiet
cls
echo.
echo [1] Interface Graphique (Recommandé)
echo [2] Console (Expert)
echo.
set /p c="[ CHOICE ] : "
if "%c%"=="2" (
    python secu_files.py
) else (
    python gui.py
)
call deactivate
pause
