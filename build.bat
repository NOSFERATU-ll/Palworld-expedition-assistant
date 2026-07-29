@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --uac-admin --name PalworldExpeditionAssistant app.py
echo.
echo Готовый EXE: dist\PalworldExpeditionAssistant.exe
pause
