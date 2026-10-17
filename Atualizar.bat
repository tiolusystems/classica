@echo off
setlocal
cd /d "%~dp0"
title Classica - Atualizar componentes
echo Feche a janela de execucao da Classica antes de continuar.
pause
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" -Update
if errorlevel 1 (
  echo Confira o erro acima e tente novamente com a internet conectada.
  pause
  exit /b 1
)
endlocal
