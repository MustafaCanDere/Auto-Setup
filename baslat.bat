@echo off
chcp 65001 >nul 2>&1
title Atolye - Muhendis Kurulum Merkezi
cd /d "%~dp0"

echo ============================================================================
echo   ATOLYE BASLATILIYOR...
echo   AI - Yazilim - Donanim ve Gomulu - DevOps - Verimlilik
echo ============================================================================
echo.

REM 1. YONETICI YETKI DURUMU
net session >nul 2>&1
if %errorlevel% equ 0 goto :IS_ADMIN
echo [BILGI] Standart kullanici modu.
goto :ADMIN_DONE

:IS_ADMIN
echo [OK] Yonetici modu aktif.

:ADMIN_DONE
echo.

REM 2. PYTHON MOTORU TESPITI
set "PYTHON_RUNNER="

REM 2.1 py -3 kontrolu
py -3 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_RUNNER=py -3"
    goto :PYTHON_OK
)

REM 2.2 py kontrolu
py -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_RUNNER=py"
    goto :PYTHON_OK
)

REM 2.3 python kontrolu
python -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_RUNNER=python"
    goto :PYTHON_OK
)

REM 2.4 python3 kontrolu
python3 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_RUNNER=python3"
    goto :PYTHON_OK
)

REM 2.5 Standart yukleme konumlari
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PYTHON_RUNNER=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_RUNNER=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_RUNNER=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_RUNNER=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK

if exist "%ProgramFiles%\Python314\python.exe" set "PYTHON_RUNNER=%ProgramFiles%\Python314\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK
if exist "%ProgramFiles%\Python313\python.exe" set "PYTHON_RUNNER=%ProgramFiles%\Python313\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK
if exist "%ProgramFiles%\Python312\python.exe" set "PYTHON_RUNNER=%ProgramFiles%\Python312\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK

if exist "%ProgramFiles(x86)%\Python314-32\python.exe" set "PYTHON_RUNNER=%ProgramFiles(x86)%\Python314-32\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK
if exist "%ProgramFiles(x86)%\Python313-32\python.exe" set "PYTHON_RUNNER=%ProgramFiles(x86)%\Python313-32\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK
if exist "%ProgramFiles(x86)%\Python312-32\python.exe" set "PYTHON_RUNNER=%ProgramFiles(x86)%\Python312-32\python.exe"
if defined PYTHON_RUNNER goto :PYTHON_OK

REM 2.6 Otomatik Python Kurulumu
echo [!] Sistemde calisan bir Python motoru bulunamadi!
echo [*] Winget uzerinden Python yuklenmeye calisiliyor...
echo.

winget --version >nul 2>&1
if %errorlevel% neq 0 goto :PYTHON_NOT_FOUND

echo Winget bulundu. Python 3.12 yukleniyor, lutfen bekleyin...
winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
echo.
echo [OK] Kurulum tamamlandi. Ortam degiskenleri yenileniyor...
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

py -3 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_RUNNER=py -3"
    goto :PYTHON_OK
)

python -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_RUNNER=python"
    goto :PYTHON_OK
)

:PYTHON_NOT_FOUND
echo ============================================================================
echo [HATA] Python calistirilamadi!
echo Lutfen https://www.python.org/downloads/ adresinden Python'u indirip kurun.
echo Kurulum ekraninda 'Add Python to PATH' kutusunu isaretlemeyi unutmayin!
echo ============================================================================
echo.
pause
exit /b 1

:PYTHON_OK
echo [OK] Python motoru aktif: %PYTHON_RUNNER%
echo [*] Atolye arayuzu aciliyor...
echo.

REM 3. PYTHON GUI ARAYUZUNU BASLAT
%PYTHON_RUNNER% "%~dp0atolye.py"

if %errorlevel% neq 0 (
    echo.
    echo ============================================================================
    echo [!] Program bir hata ile kapandi. Hata Kodu: %errorlevel%
    echo ============================================================================
    echo.
    pause
)

exit /b 0
