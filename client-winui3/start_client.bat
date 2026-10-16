@echo off
title IntanWave Node (Official WinUI 3)
cd /d "%~dp0"

set "DOTNET_PATH=%LOCALAPPDATA%\Microsoft\dotnet\dotnet.exe"
if exist "%DOTNET_PATH%" (
    "%DOTNET_PATH%" run --project IntanWaveNode.csproj %*
    exit /b 0
)

dotnet run --project IntanWaveNode.csproj %*
