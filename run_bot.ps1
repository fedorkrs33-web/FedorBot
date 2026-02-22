# Задаём кодировку UTF-8
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding

# Переход в директорию проекта
Set-Location -Path "c:\\Work\\FedorBot"
Write-Host "Переход в директорию проекта: $((Get-Item $(Get-Location)).FullName)" -ForegroundColor Green

# Проверка существования директории
if (-not (Test-Path ".")) {
    Write-Host "Ошибка: директория проекта не найдена!" -ForegroundColor Red
    Pause
    exit 1
}

# Активация виртуального окружения
$venvActivate = "c:\\Work\\FedorBot\\.venv\\Scripts\\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "Активация виртуального окружения..." -ForegroundColor Green
    & $venvActivate
} else {
    Write-Host "Ошибка: виртуальное окружение не найдено. Выполните: python -m venv .venv" -ForegroundColor Red
    Pause
    exit 1
}

# Настройка переменной окружения PATH
$env:PATH += ";$env:USERPROFILE"
Write-Host "Переменная PATH обновлена." -ForegroundColor Green

# Запуск бота
Write-Host "Запуск бота..." -ForegroundColor Yellow
python -m src.bot

# Пауза перед закрытием (работает как Read-Host для удержания окна)
Write-Host "Нажмите Enter для выхода..." -ForegroundColor Gray
Read-Host
