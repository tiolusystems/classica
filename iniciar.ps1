param([switch]$Update, [switch]$SetupOnly, [switch]$Background)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Set-Location -LiteralPath $PSScriptRoot
$toolsDir = Join-Path $PSScriptRoot '.tools'
$binDir = Join-Path $toolsDir 'bin'
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$uvExe = Join-Path $binDir 'uv.exe'
$headers = @{ 'User-Agent' = 'Classica/2.3.0'; 'Accept' = 'application/vnd.github+json' }
$toolsLock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'tools.lock.json') -Raw | ConvertFrom-Json

function Install-ReleaseZip([string]$Repository, [string]$Destination, [string]$Executable) {
    Write-Host "Preparando $Repository. Aguarde o download..." -ForegroundColor DarkGreen
    $locked = $toolsLock.windows_x64 | Where-Object { $_.repository -eq $Repository } | Select-Object -First 1
    if (-not $locked -or $locked.sha256 -notmatch '^[a-f0-9]{64}$') { throw "Componente sem hash valido: $Repository" }
    $allowedPrefix = 'https://github.com/' + $Repository + '/releases/download/'
    if (-not $locked.url.StartsWith($allowedPrefix)) { throw 'Origem do componente invalida.' }
    $AssetName = $locked.asset
    $workDir = Join-Path $toolsDir ('temp-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $workDir | Out-Null
    try {
        $archive = Join-Path $workDir 'package.zip'
        Invoke-WebRequest -UseBasicParsing -Uri $locked.url -Headers $headers -OutFile $archive -TimeoutSec 1800
        $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
        if ($actual -ne $locked.sha256) { throw "Falha SHA256 de $AssetName. O arquivo nao sera executado." }
        $expanded = Join-Path $workDir 'expanded'
        Expand-Archive -LiteralPath $archive -DestinationPath $expanded -Force
        $binary = Get-ChildItem -LiteralPath $expanded -Recurse -Filter $Executable | Select-Object -First 1
        if (-not $binary) { throw "Componente $Executable nao encontrado no pacote oficial." }
        if ($Executable -eq 'ffmpeg.exe') {
            $probe = Get-ChildItem -LiteralPath $expanded -Recurse -Filter 'ffprobe.exe' | Select-Object -First 1
            if (-not $probe) { throw 'FFprobe ausente no pacote FFmpeg.' }
            # Keep the original docs and licensing files with the downloaded tools.
            if (Test-Path -LiteralPath $Destination) { Remove-Item -LiteralPath $Destination -Recurse -Force }
            Move-Item -LiteralPath $expanded -Destination $Destination
        } else {
            New-Item -ItemType Directory -Force -Path $Destination | Out-Null
            Copy-Item -LiteralPath $binary.FullName -Destination (Join-Path $Destination $Executable) -Force
        }
        $record = [ordered]@{ repository=$Repository; version=$locked.tag; asset=$AssetName; digest=('sha256:' + $locked.sha256); installed=(Get-Date).ToString('o') }
        $record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $toolsDir ($Executable + '.json')) -Encoding UTF8
    } finally {
        Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

try {
    if ($PSScriptRoot.TrimEnd('\') -eq [IO.Path]::GetPathRoot($PSScriptRoot).TrimEnd('\')) {
        throw 'A aplicacao deve ficar em uma pasta propria, por exemplo C:\Classica. Extraia a pasta Classica do ZIP e abra Iniciar.bat dentro dela.'
    }
    Start-Transcript -Path (Join-Path $PSScriptRoot 'ultimo-inicio.log') -Force | Out-Null
    Write-Host ''
    Write-Host ('CLASSICA 2.3.0 - Audio e video | by ' + [char]0x2627 + ' SYSTEMS') -ForegroundColor DarkGreen
    Write-Host 'Na primeira abertura, os componentes gratuitos serao baixados automaticamente.'
    Write-Host 'Reserve cerca de 2 GB livres. A preparacao pode levar alguns minutos.'
    Write-Host 'Nenhuma senha, conta ou chave de API e necessaria.'
    Write-Host ''
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Esta versao requer Windows de 64 bits.' }
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
        throw 'Este pacote foi preparado para Windows x64 (Intel/AMD). Um pacote ARM64 e necessario neste computador.'
    }
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    $setupLock = Join-Path $toolsDir 'preparacao.lock'
    try { $lockStream = [IO.File]::Open($setupLock, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) }
    catch { throw 'Outra janela da Classica esta preparando os componentes. Aguarde e use essa janela.' }
    if (-not (Test-Path -LiteralPath $uvExe)) {
        Install-ReleaseZip 'astral-sh/uv' $binDir 'uv.exe'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $binDir 'deno.exe'))) {
        Install-ReleaseZip 'denoland/deno' $binDir 'deno.exe'
    }
    $ffmpegDir = Join-Path $toolsDir 'ffmpeg'
    $ffmpeg = Get-ChildItem -LiteralPath $ffmpegDir -Recurse -Filter 'ffmpeg.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
    $ffprobe = Get-ChildItem -LiteralPath $ffmpegDir -Recurse -Filter 'ffprobe.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $ffmpeg -or -not $ffprobe) {
        Install-ReleaseZip 'yt-dlp/FFmpeg-Builds' $ffmpegDir 'ffmpeg.exe'
        $ffmpeg = Get-ChildItem -LiteralPath $ffmpegDir -Recurse -Filter 'ffmpeg.exe' | Select-Object -First 1
    }
    $env:PATH = $binDir + ';' + $ffmpeg.DirectoryName + ';' + $env:PATH
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $toolsDir 'python'
    $env:UV_PYTHON_BIN_DIR = $binDir
    $env:UV_CACHE_DIR = Join-Path $toolsDir 'cache'
    $env:PYTHONUTF8 = '1'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        Write-Host 'Preparando Python local, sem alterar o Python do seu sistema...'
        & $uvExe python install '3.13'
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar Python. Confira a conexao.' }
        & $uvExe venv --python '3.13' (Join-Path $PSScriptRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o ambiente da aplicacao.' }
    }
    $readyFile = Join-Path $toolsDir 'dependencias-prontas'
    $lockPath = Join-Path $PSScriptRoot 'requirements.lock'
    $lockDigest = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
    $installedLock = if (Test-Path -LiteralPath $readyFile) { (Get-Content -LiteralPath $readyFile -Raw).Trim() } else { '' }
    if ($Update -or $installedLock -ne $lockDigest) {
        Write-Host 'Instalando ou atualizando o extrator de audio e video...'
        if ($Update) {
            & $uvExe pip install --python $pythonExe --upgrade 'yt-dlp[default]'
        } else {
            & $uvExe pip install --python $pythonExe --require-hashes -r $lockPath
        }
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar yt-dlp. Confira a conexao e tente novamente.' }
        Set-Content -LiteralPath $readyFile -Value $lockDigest
        if ($Update) { Set-Content -LiteralPath (Join-Path $toolsDir 'perfil-atualizado.txt') -Value (Get-Date).ToString('o') }
    }
    $lockStream.Dispose()
    $lockStream = $null
    if ($SetupOnly) { Stop-Transcript | Out-Null; exit 0 }
    if ($Background) {
        # Opt-in background process: original console-based Iniciar.bat remains unchanged.
        # Each launch owns its streams. Reopening must not truncate or lock the
        # output file still held by the existing background server.
        $launchLogs = Join-Path $toolsDir ('logs\' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Force -Path $launchLogs | Out-Null
        $outputLog = Join-Path $launchLogs 'saida.log'
        $errorLog = Join-Path $launchLogs 'erros.log'
        $lastOutput = Join-Path $PSScriptRoot 'ultimo-discreto.log'
        $lastError = Join-Path $PSScriptRoot 'ultimo-discreto-erros.log'
        $appScript = Join-Path $PSScriptRoot 'app.py'
        Write-Host 'Iniciando a Classica em segundo plano. Use Sair na interface para encerrar.'
        $arguments = ('"{0}"' -f $appScript)
        $child = Start-Process -FilePath $pythonExe -WorkingDirectory $PSScriptRoot -ArgumentList $arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog
        try {
            $ready = $false
            for ($attempt = 0; $attempt -lt 120; $attempt++) {
                Start-Sleep -Milliseconds 250
                if ($child.HasExited -and $child.ExitCode -ne 0) {
                    $details = if (Test-Path -LiteralPath $errorLog) { [string](Get-Content -LiteralPath $errorLog -Raw) } else { '' }
                    if (Test-Path -LiteralPath $outputLog) { $details += [string](Get-Content -LiteralPath $outputLog -Raw) }
                    throw ('Nao foi possivel iniciar a Classica sem janela. ' + $details + ' Consulte ultimo-discreto-erros.log.')
                }
                $output = if (Test-Path -LiteralPath $outputLog) { [string](Get-Content -LiteralPath $outputLog -Raw) } else { '' }
                if ($output -match 'http://127\.0\.0\.1:\d+') { $ready = $true; break }
                if ($child.HasExited) { throw 'A Classica encerrou sem informar o endereco local. Consulte ultimo-discreto.log.' }
            }
            if (-not $ready) { throw 'A Clássica não confirmou a inicialização em 30 segundos. Confira ultimo-discreto-erros.log.' }
            Copy-Item -LiteralPath $outputLog -Destination $lastOutput -Force
            Copy-Item -LiteralPath $errorLog -Destination $lastError -Force
            Write-Host ('Registro completo desta abertura: ' + $launchLogs)
            Write-Host 'Clássica aberta no navegador; a janela de inicialização pode ser fechada.'
            Stop-Transcript | Out-Null
            exit 0
        } catch {
            if (Test-Path -LiteralPath $outputLog) { Copy-Item -LiteralPath $outputLog -Destination $lastOutput -Force -ErrorAction SilentlyContinue }
            if (Test-Path -LiteralPath $errorLog) { Copy-Item -LiteralPath $errorLog -Destination $lastError -Force -ErrorAction SilentlyContinue }
            if (-not $child.HasExited) { Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue }
            throw
        }
    }
    Write-Host 'Tudo pronto. Abrindo sua biblioteca no navegador...' -ForegroundColor DarkGreen
    & $pythonExe (Join-Path $PSScriptRoot 'app.py')
    if ($LASTEXITCODE -ne 0) { throw 'A aplicacao foi encerrada com erro. Veja os detalhes acima.' }
    Stop-Transcript | Out-Null
    exit 0
} catch {
    Write-Host ''
    Write-Host ('ERRO: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Abra a pasta extraida, confira a internet e tente Iniciar.bat novamente.'
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
} finally {
    if ($lockStream) { $lockStream.Dispose() }
}
