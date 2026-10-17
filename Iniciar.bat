@echo off
setlocal
cd /d "%~dp0"
title Classica - Biblioteca de musica
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo Esta aplicacao requer Windows 10 ou 11 de 64 bits.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar. Confira a mensagem acima e sua conexao.
  echo Os detalhes estao no arquivo ultimo-inicio.log desta pasta.
  pause
  exit /b 1
)
endlocal
