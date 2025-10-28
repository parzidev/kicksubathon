@echo off
chcp 65001 >nul
title Kick.com Subathon Server

echo ============================================
echo   KICK.COM SUBATHON SERVER
echo ============================================
echo.

cd /d "%~dp0"

REM Python'un yüklü olup olmadığını kontrol et
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python bulunamadı! Lütfen Python'u yükleyin.
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Gerekli paketleri yükle
echo 📦 Gerekli paketler kontrol ediliyor...
pip install -r requirements.txt >nul 2>&1

echo.
echo ✅ Hazır! Server başlatılıyor...
echo.

REM Server'ı başlat
python server.py

pause


