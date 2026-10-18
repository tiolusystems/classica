# Compile our own visible, unpacked launcher using Windows' .NET Framework compiler.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Compilador .NET Framework do Windows ausente.' }
$output = Join-Path $root 'build'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$launcher = Join-Path $output ('Cl' + [char]0x00E1 + 'ssica.exe')
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /codepage:65001 `
    /reference:System.Windows.Forms.dll /reference:System.Drawing.dll `
    "/win32icon:$(Join-Path $root 'assets\classica.ico')" `
    "/win32manifest:$(Join-Path $root 'launcher\app.manifest')" `
    "/out:$launcher" (Join-Path $root 'launcher\Classica.cs')
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $launcher)) { throw 'Falha ao compilar Clássica.' }
Write-Host "Launcher compiled: $launcher"
