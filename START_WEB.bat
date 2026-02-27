@echo off
chcp 65001 >nul
title GALAXY FOOD — Запуск системы
color 0A

echo.
echo  ╔══════════════════════════════════════╗
echo  ║        GALAXY FOOD — Система         ║
echo  ║         управления кафе              ║
echo  ╚══════════════════════════════════════╝
echo.
echo  Запуск веб-интерфейса...
echo  После запуска откройте браузер:
echo.
echo     http://127.0.0.1:8080
echo.
echo  Для остановки нажмите Ctrl+C
echo.

start "" "http://127.0.0.1:8080"
python app.py

if errorlevel 1 (
    echo.
    echo  ОШИБКА! Убедитесь что Python установлен.
    echo  Установите зависимости: pip install -r requirements.txt
    pause
)
