@echo off
setlocal
cd /d "%~dp0"
title Classica - Inicializacao discreta
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo Este modo requer PowerShell no Windows 10/11.
  pause
  exit /b 1
)
echo Preparando a Classica. A janela sera fechada apos a abertura do navegador.
echo Depois, para encerrar o programa, use Sair na interface.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" -Background
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar em segundo plano.
  echo Consulte ultimo-inicio.log e ultimo-discreto-erros.log na pasta da Classica.
  echo Como alternativa, use Iniciar.bat.
  pause
  exit /b 1
)
endlocal
