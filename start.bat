@echo off
where python >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato nel PATH.
    echo Scarica Python da: https://www.python.org/downloads/
    pause
    exit /b 1
)
python "%~dp0start.py"
pause
