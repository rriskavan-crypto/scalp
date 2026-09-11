@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title ScalpKit - o'rnatish

echo.
echo ==================================================================
echo    SCALPKIT - AVTOMATIK O'RNATISH (Windows)
echo ==================================================================
echo.

cd /d "%~dp0"
echo Papka: %CD%
echo.

REM ---------- 1. Python topish ----------
echo [1/6] Python qidirilmoqda...
set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE (
    where python >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
    echo.
    echo   XATO: Python topilmadi.
    echo.
    echo   Yechim: https://www.python.org/downloads/ dan Python 3.11 ni
    echo   yuklab oling. O'rnatishda "Add python.exe to PATH" katakchasini
    echo   ALBATTA belgilang, keyin bu faylni qaytadan ishga tushiring.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PYEXE% --version 2^>^&1') do set "PYVER=%%v"
echo   topildi: Python !PYVER!

REM 3.10 dan past bo'lmasin
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set "MAJ=%%a"
    set "MIN=%%b"
)
if !MAJ! LSS 3 goto :oldpy
if !MAJ! EQU 3 if !MIN! LSS 10 goto :oldpy
goto :pyok

:oldpy
echo.
echo   XATO: Python !PYVER! juda eski. Kamida 3.10 kerak.
echo   https://www.python.org/downloads/ dan yangisini o'rnating.
echo.
pause
exit /b 1

:pyok
echo.

REM ---------- 2. Virtual muhit ----------
echo [2/6] Virtual muhit (.venv) tayyorlanmoqda...
if exist ".venv\Scripts\python.exe" (
    echo   mavjud - qayta ishlatiladi
) else (
    %PYEXE% -m venv .venv
    if errorlevel 1 (
        echo.
        echo   XATO: virtual muhit yaratilmadi.
        echo   Python o'rnatmasi to'liq emas bo'lishi mumkin.
        echo.
        pause
        exit /b 1
    )
    echo   yaratildi
)
set "VPY=%CD%\.venv\Scripts\python.exe"
echo.

REM ---------- 3. pip ----------
echo [3/6] pip yangilanmoqda...
"%VPY%" -m pip install --quiet --upgrade pip setuptools wheel
if errorlevel 1 (
    echo   OGOHLANTIRISH: pip yangilanmadi - davom etamiz
)
echo   tayyor
echo.

REM ---------- 4. Kutubxonalar ----------
echo [4/6] Kutubxonalar o'rnatilmoqda (bir-ikki daqiqa)...
"%VPY%" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo.
    echo   XATO: asosiy kutubxonalar o'rnatilmadi.
    echo   Internetni tekshiring va qaytadan urinib ko'ring.
    echo.
    pause
    exit /b 1
)
echo   numpy, pandas, PyYAML, requests - tayyor

"%VPY%" -m pip install --quiet pytest
echo   pytest - tayyor

REM MetaTrader5 faqat Windows uchun
"%VPY%" -m pip install --quiet MetaTrader5
if errorlevel 1 (
    echo   OGOHLANTIRISH: MetaTrader5 paketi o'rnatilmadi.
    echo   Backtest ishlaydi, lekin MT5 ga ulanish ishlamaydi.
    echo   Sabab odatda: 64-bitli Python kerak.
) else (
    echo   MetaTrader5 - tayyor
)

"%VPY%" -m pip install --quiet -e .
echo.

REM ---------- 5. Tekshiruv ----------
echo [5/6] Testlar ishga tushirilmoqda...
"%VPY%" -m pytest -q
if errorlevel 1 (
    echo.
    echo   OGOHLANTIRISH: ba'zi testlar yiqildi.
    echo   Yuqoridagi matnni menga yuboring.
    echo.
) else (
    echo.
    echo   HAMMA TEST O'TDI
)
echo.

REM ---------- 6. Qulaylik ----------
echo [6/6] scalpkit.bat yorlig'i yaratilmoqda...
> scalpkit.bat echo @echo off
>> scalpkit.bat echo "%%~dp0.venv\Scripts\python.exe" -m scalpkit %%*
echo   tayyor
echo.

echo ==================================================================
echo    O'RNATILDI
echo ==================================================================
echo.
echo Endi shu papkada quyidagi buyruqlarni ishlatishingiz mumkin:
echo.
echo    scalpkit profiles
echo    scalpkit costs --profile btcusd_5m
echo    scalpkit mt5-test --symbol BTCUSD
echo    scalpkit mt5-bars --symbol BTCUSD --interval 15m --count 200000 --out data\BTCUSD_15m.csv
echo    scalpkit validate --profile btcusd_15m --data data\BTCUSD_15m.csv --strategy donchian_breakout
echo.
echo MT5 ga ulanish uchun avval parolni qo'ying (har safar yangi oynada):
echo.
echo    set MT5_PASSWORD=parolingiz
echo.
echo Birinchi qadam sifatida shuni bosing:
echo.
echo    scalpkit profiles
echo.
pause
