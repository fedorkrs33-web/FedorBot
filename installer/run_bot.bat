@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
) else (
  echo Создайте виртуальное окружение: python -m venv .venv
  pause
  exit /b 1
)
python -m src.bot
pause
