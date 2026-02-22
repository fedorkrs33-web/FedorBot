@echo off
chcp 65001 >nul

cd /d "c:\Work\FedorBot"

echo Переход в директорию проекта...
if not exist "c:\Work\FedorBot" (
    echo Ошибка: директория проекта не найдена!
    pause
    exit /b 1
)

echo Активация виртуального окружения...
if exist "c:\Work\FedorBot\.venv\Scripts\activate.bat" (
    call "c:\Work\FedorBot\.venv\Scripts\activate.bat"
) else (
    echo Ошибка: виртуальное окружение не найдено. Выполните: python -m venv .venv
    pause
    exit /b 1
)

echo Настройка переменной окружения PATH...
set "PATH=%PATH%;%USERPROFILE%"

echo Запуск бота...
python -m src.bot

pause
