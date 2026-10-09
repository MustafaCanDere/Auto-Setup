@echo off
title Muhendis Super Kurulum Merkezi
cd /d "%~dp0"
call "%~dp0baslat.bat" %*
if %errorlevel% neq 0 (
    echo.
    echo Bir hata olustu. Kapatmak icin bir tusa basin...
    pause >nul
)
