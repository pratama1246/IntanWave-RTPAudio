@echo off
title IntanWave Node Launcher
cd /d "%~dp0"

if exist "dist\IntanWave-Node\IntanWave-Node.exe" (
    start "" "dist\IntanWave-Node\IntanWave-Node.exe"
    exit
)

if exist "IntanWave-Node\IntanWave-Node.exe" (
    start "" "IntanWave-Node\IntanWave-Node.exe"
    exit
)

if exist "IntanWave-Node.exe" (
    start "" "IntanWave-Node.exe"
    exit
)

start "" pythonw app.py
exit
