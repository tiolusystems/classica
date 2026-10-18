param([Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{32}$')][string]$ActionId)
# This helper only switches a package already staged and hashed by our server.
# It never changes the downloaded/portable source folder or user history.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$components = Split-Path -Parent $PSScriptRoot
$oldPackage = Split-Path -Parent $components
$profileDir = Join-Path $env:LOCALAPPDATA 'Classica'
$managed = Join-Path $env:LOCALAPPDATA 'Programs\Classica'
$pointer = Join-Path $profileDir 'instalacao.json'
$sessionFile = Join-Path $profileDir 'instancia.json'
$exeName = 'Cl' + [char]0x00E1 + 'ssica.exe'
$powershell = Join-Path ([Environment]::GetFolderPath('System')) 'WindowsPowerShell\v1.0\powershell.exe'
$transitioned = $false
$newProcess = $null
$previousPointer = if (Test-Path -LiteralPath $pointer) { [IO.File]::ReadAllText($pointer) } else { $null }
$logDir = Join-Path $profileDir ('manutencao\' + $ActionId)
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-AtomicJson($Path, $Value) {
    $temporary = $Path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}
function Read-Session($ExpectedComponents, $ExpectedVersion) {
    $item = Get-Item -LiteralPath $sessionFile
    if ($item.Length -gt 16384) { throw 'Sessao local invalida.' }
    $record = [IO.File]::ReadAllText($sessionFile) | ConvertFrom-Json
    if ($record.url -notmatch '^http://127\.0\.0\.1:[1-9][0-9]{0,4}$' -or $record.token -notmatch '^[A-Za-z0-9_-]{32,128}$' -or
        [IO.Path]::GetFullPath($record.directory).TrimEnd('\') -ne [IO.Path]::GetFullPath($ExpectedComponents).TrimEnd('\') -or
        $record.version -ne $ExpectedVersion) { throw 'A sessao pertence a outra versao.' }
    $live = Invoke-RestMethod -Uri ($record.url + '/api/instance') -Headers @{'X-Classica-Token'=$record.token} -TimeoutSec 4 -MaximumRedirection 0
    if ($live.pid -ne $record.pid -or $live.version -ne $record.version -or $live.directory -ne $record.directory -or $live.closing) { throw 'A sessao local nao foi confirmada.' }
    return $record
}
function Post-Local($Session, $Route, $Body) {
    Invoke-RestMethod -Uri ($Session.url + '/api/' + $Route) -Headers @{'X-Classica-Token'=$Session.token} -Method Post -ContentType 'application/json' -Body ($Body | ConvertTo-Json -Compress) -TimeoutSec 8 -MaximumRedirection 0
}
function Run-Preparation($Directory, $Option, $Label) {
    Write-Host $Label
    $outLog = Join-Path $logDir ($Option.TrimStart('-') + '-saida.log')
    $errLog = Join-Path $logDir ($Option.TrimStart('-') + '-erros.log')
    $arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" {1}' -f (Join-Path $Directory 'iniciar.ps1'), $Option
    $process = Start-Process -FilePath $powershell -ArgumentList $arguments -WorkingDirectory $Directory -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    $null = $process.Handle
    while (-not $process.WaitForExit(250)) { }
    if ($process.ExitCode -ne 0) {
        Get-Content -LiteralPath $outLog -Tail 20 -ErrorAction SilentlyContinue | Write-Host
        Get-Content -LiteralPath $errLog -Tail 20 -ErrorAction SilentlyContinue | Write-Host
        throw 'A preparacao dos componentes falhou. A versao atual foi preservada.'
    }
    $process.Dispose()
}
function Set-Shortcut($Directory, $Target) {
    if (-not $Directory) { return }
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    $path = Join-Path $Directory ('Cl' + [char]0x00E1 + 'ssica.lnk')
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($path)
    if ((Test-Path -LiteralPath $path) -and $shortcut.TargetPath -ne $Target -and
        -not $shortcut.TargetPath.StartsWith($managed + '\', [StringComparison]::OrdinalIgnoreCase)) {
        Write-Host 'Um atalho de outro aplicativo foi preservado.'; return
    }
    $shortcut.TargetPath = $Target; $shortcut.WorkingDirectory = $managed
    $shortcut.IconLocation = $Target + ',0'; $shortcut.Description = 'Classica - audio e video - by SYSTEMS'
    $shortcut.Save()
}

try {
    $oldVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo((Join-Path $oldPackage $exeName)).FileVersion -replace '\.0$', ''
    $oldSession = Read-Session $components $oldVersion
    $desktop = Invoke-RestMethod -Uri ($oldSession.url + '/api/desktop') -Headers @{'X-Classica-Token'=$oldSession.token} -TimeoutSec 4 -MaximumRedirection 0
    $action = $desktop.action
    if (-not $action -or $action.id -ne $ActionId -or $action.version -notmatch '^\d+\.\d+\.\d+$' -or $desktop.pending -ne 0) { throw 'Preparacao nao reconhecida.' }
    $target = Join-Path $managed ('versoes\Classica-' + $action.version)
    if ([IO.Path]::GetFullPath($action.target).TrimEnd('\') -ne [IO.Path]::GetFullPath($target).TrimEnd('\')) { throw 'Destino de instalacao invalido.' }
    # Refuse junctions/symlinks, including parents, before executing any file.
    $ancestor = Get-Item -LiteralPath $target
    while ($ancestor) {
        if ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'O destino contem um vinculo de pasta nao permitido.' }
        $ancestor = $ancestor.Parent
    }
    if (@(Get-ChildItem -LiteralPath $target -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw 'O pacote contem um vinculo nao permitido.' }
    $manifest = [IO.File]::ReadAllText((Join-Path $target '.classica-package.json')) | ConvertFrom-Json
    if ($manifest.version -ne $action.version) { throw 'Versao do pacote invalida.' }
    foreach ($file in $manifest.files.PSObject.Properties) {
        $full = [IO.Path]::GetFullPath((Join-Path $target $file.Name))
        if (-not $full.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase) -or $file.Value -notmatch '^[a-f0-9]{64}$' -or
            (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.Value) { throw 'A verificacao dos arquivos falhou.' }
    }
    $targetComponents = Join-Path $target 'Componentes'
    $targetExe = Join-Path $target $exeName
    $check = Start-Process -FilePath $targetExe -ArgumentList '--check' -PassThru -Wait
    if ($check.ExitCode -ne 0) { throw 'A nova versao nao passou na verificacao inicial.' }
    Run-Preparation $targetComponents '-SetupOnly' 'Preparando os componentes da versao selecionada. A versao atual continua aberta.'
    Write-Host 'Componentes prontos. Abrindo a versao preparada...'
    Post-Local $oldSession 'desktop/transition' @{id=$ActionId} | Out-Null
    $transitioned = $true
    $newProcess = Start-Process -FilePath $targetExe -WorkingDirectory $target -PassThru
    $ready = $null
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Milliseconds 500
        try { $ready = Read-Session $targetComponents $action.version; break } catch { }
        if ($newProcess.HasExited) { throw 'A nova versao encerrou antes de ficar pronta.' }
    }
    if (-not $ready) { throw 'A nova versao nao respondeu no prazo esperado.' }
    $previous = if ($previousPointer) { ($previousPointer | ConvertFrom-Json).previous } else { $null }
    if ($oldVersion -ne $action.version) { $previous = @{directory=$oldPackage; version=$oldVersion} }
    $stable = Join-Path $managed $exeName
    # A stable forwarding launcher lets existing shortcuts follow every switch,
    # including a rollback to a version that predates the desktop controller.
    if (-not (Test-Path -LiteralPath $stable)) { Copy-Item -LiteralPath (Join-Path $oldPackage $exeName) -Destination $stable }
    Write-AtomicJson $pointer @{current=@{directory=$target; version=$action.version}; previous=$previous}
    Set-Shortcut ([Environment]::GetFolderPath('DesktopDirectory')) $stable
    Set-Shortcut ([Environment]::GetFolderPath('Programs')) $stable
    Write-Host 'Pronto. Versao aberta; historico, preferencias e arquivos preservados.'
    exit 0
}
catch {
    Write-Host ('Nao foi possivel concluir: ' + $_.Exception.Message)
    if ($transitioned) {
        try {
            $candidate = Read-Session $targetComponents $action.version
            Post-Local $candidate 'shutdown' @{} | Out-Null
        } catch { }
        if ($newProcess -and -not $newProcess.WaitForExit(8000)) { Stop-Process -Id $newProcess.Id -Force -ErrorAction SilentlyContinue }
        if ($previousPointer) { Write-AtomicJson $pointer ($previousPointer | ConvertFrom-Json) }
        elseif (Test-Path -LiteralPath $pointer) { Remove-Item -LiteralPath $pointer -Force }
        try { Run-Preparation $components '-Background' 'Reabrindo a versao anterior...'; Write-Host 'A versao anterior foi reaberta.' } catch { Write-Host 'Abra novamente a versao anterior pela pasta original.' }
    }
    try { Post-Local $oldSession 'desktop/failed' @{id=$ActionId} | Out-Null } catch { }
    exit 1
}
