@echo off
title IntanWave Node (C# Client)
cd /d "%~dp0"

set "EXE_PATH=bin\Debug\net8.0-windows\IntanWave-Node.exe"
if exist "%EXE_PATH%" (
    start "" "%EXE_PATH%" %*
    exit /b 0
)

set "DOTNET_PATH=%LOCALAPPDATA%\Microsoft\dotnet\dotnet.exe"
if exist "%DOTNET_PATH%" (
    start "" "%DOTNET_PATH%" run --project IntanWave.Node.csproj %*
    exit /b 0
)

dotnet run --project IntanWave.Node.csproj %*
