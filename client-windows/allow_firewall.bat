@echo off
:: Batch script untuk membuka port firewall UDP 5004 IntanWave Node
title Izinkan Firewall IntanWave Node
echo Menambahkan aturan Firewall untuk IntanWave Node...
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [PERINGATAN] Silakan jalankan file ini dengan cara: Klik Kanan -^> 'Run as administrator'
    pause
    exit /b
)

netsh advfirewall firewall add rule name="IntanWave Node Audio (UDP 5004)" dir=in action=allow protocol=UDP localport=5004 profile=any

echo.
echo [SUKSES] Port UDP 5004 berhasil diizinkan di Windows Firewall!
pause
