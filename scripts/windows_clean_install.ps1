# Windows GitHub Actions integration test. Never run on a user's workstation.
param([Parameter(Mandatory=$true)][string]$Archive)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) {
    throw 'This test runs only on an isolated GitHub Actions Windows runner.'
}

$archivePath = (Resolve-Path -LiteralPath $Archive).Path
$checksumPath = $archivePath + '.sha256'
if (-not (Test-Path -LiteralPath $checksumPath)) {
    throw 'Missing SHA256 file for release ZIP.'
}
$expected = ((Get-Content -LiteralPath $checksumPath -Raw).Trim() -split '\s+')[0].ToLowerInvariant()
$actual = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expected -notmatch '^[0-9a-f]{64}$' -or $actual -ne $expected) {
    throw 'Windows ZIP checksum mismatch.'
}

$workspace = Join-Path $env:RUNNER_TEMP ('Classica espa' + [char]0x00E7 + 'o & acento-classica-zip-clean-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
$serverProcess = $null
try {
    Expand-Archive -LiteralPath $archivePath -DestinationPath $workspace
    $packageDir = Join-Path $workspace 'Classica-2.4.1'
    $appDir = Join-Path $packageDir 'Componentes'
    $launcherName = 'Cl' + [char]0x00E1 + 'ssica.exe'
    $launcher = Join-Path $packageDir $launcherName
    $publicItems = @(Get-ChildItem -LiteralPath $packageDir -Force | Select-Object -ExpandProperty Name)
    if (@(Compare-Object $publicItems @($launcherName, 'Leia-me.txt', 'Componentes')).Count -ne 0) {
        throw 'Distribution root must have one branded launcher, user guide and components folder only.'
    }
    if (-not (Test-Path -LiteralPath $launcher)) { throw 'Branded launcher missing from ZIP.' }
    $version = [Diagnostics.FileVersionInfo]::GetVersionInfo($launcher)
    if ($version.FileVersion -ne '2.4.1.0') { throw 'Launcher version mismatch.' }
    Add-Type -AssemblyName System.Drawing
    $icon = [Drawing.Icon]::ExtractAssociatedIcon($launcher)
    if (-not $icon) { throw 'Launcher icon missing.' }
    $icon.Dispose()
    $probe = Start-Process -FilePath $launcher -ArgumentList '--check' -WorkingDirectory $env:RUNNER_TEMP -PassThru -Wait
    if ($probe.ExitCode -ne 0) { throw 'Launcher failed package check from unrelated working directory.' }
    $mixed = Join-Path $workspace 'mixed-files'
    $mixedComponents = Join-Path $mixed 'Componentes'
    New-Item -ItemType Directory -Force -Path (Join-Path $mixedComponents 'web') | Out-Null
    Copy-Item -LiteralPath $launcher -Destination $mixed
    foreach ($required in @('iniciar.ps1', 'tools.lock.json', 'requirements.lock', 'web/index.html')) {
        Copy-Item -LiteralPath (Join-Path $appDir $required) -Destination (Join-Path $mixedComponents $required)
    }
    Set-Content -LiteralPath (Join-Path $mixedComponents 'app.py') -Value 'VERSION = "0.0.0"' -Encoding UTF8
    $mixedCheck = Start-Process -FilePath (Join-Path $mixed ([IO.Path]::GetFileName($launcher))) -ArgumentList '--check' -PassThru -Wait
    if ($mixedCheck.ExitCode -ne 1) { throw 'Launcher accepted mixed release files.' }
    Write-Host 'Branded launcher rejects mixed release files: PASS'
    if (-not (Test-Path -LiteralPath (Join-Path $appDir 'Iniciar.bat')) -or
        -not (Test-Path -LiteralPath (Join-Path $appDir 'iniciar.ps1'))) {
        throw 'Release ZIP does not contain the required Classica/ launcher.'
    }
    if (Test-Path -LiteralPath (Join-Path $appDir '.venv')) {
        throw 'The ZIP unexpectedly contains a Python environment.'
    }
    if (Test-Path -LiteralPath (Join-Path $appDir '.tools')) {
        throw 'The ZIP unexpectedly contains downloaded third-party tools.'
    }

    # A fresh ZIP must independently provision all runtime components.
    Push-Location -LiteralPath $appDir
    try {
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $appDir 'iniciar.ps1') -SetupOnly
        if ($LASTEXITCODE -ne 0) {
            throw "Clean setup failed with exit code $LASTEXITCODE."
        }
    }
    finally { Pop-Location }

    $pythonExe = Join-Path $appDir '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        throw 'Python interpreter missing after fresh setup.'
    }
    $binDir = Join-Path $appDir '.tools\bin'
    $ffmpeg = Get-ChildItem -LiteralPath (Join-Path $appDir '.tools\ffmpeg') -Recurse -Filter 'ffmpeg.exe' |
        Select-Object -First 1
    if (-not $ffmpeg) { throw 'FFmpeg missing after fresh setup.' }
    $ffprobe = Join-Path $ffmpeg.DirectoryName 'ffprobe.exe'
    if (-not (Test-Path -LiteralPath $ffprobe)) { throw 'FFprobe missing after fresh setup.' }
    $env:PATH = $binDir + ';' + $ffmpeg.DirectoryName + ';' + $env:PATH

    Push-Location -LiteralPath $appDir
    try {
        & $pythonExe -c "import app,pathlib; assert pathlib.Path(app.__file__).resolve().parent == pathlib.Path.cwd(); assert app.VERSION == '2.4.1'; assert all(app.dependencies().values()), app.dependencies(); print('Fresh runtime components: PASS')"
        if ($LASTEXITCODE -ne 0) { throw 'Fresh runtime import/dependencies check failed.' }
    }
    finally { Pop-Location }

    # Match the UTF-8 environment set by iniciar.ps1 for real users.
    # A plain redirected Python process can otherwise fail encoding the Chi Rho symbol
    # in Windows' default console code page (observed in CI).
    $env:PYTHONUTF8 = '1'
    # Real process + loopback HTTP, using isolated history and no browser launch.
    $dataDir = Join-Path $workspace 'isolated-user-data'
    $stdout = Join-Path $workspace 'app-stdout.log'
    $stderr = Join-Path $workspace 'app-stderr.log'
    $arguments = '"{0}" --no-browser --data-dir "{1}"' -f (Join-Path $appDir 'app.py'), $dataDir
    $serverProcess = Start-Process -FilePath $pythonExe -WorkingDirectory $appDir -ArgumentList $arguments -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $url = $null
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        Start-Sleep -Milliseconds 300
        if ($serverProcess.HasExited) {
            throw "App exited before readiness. stderr: $(Get-Content -LiteralPath $stderr -Raw)"
        }
        if (Test-Path -LiteralPath $stdout) {
            $output = [string](Get-Content -LiteralPath $stdout -Raw)
            $match = [regex]::Match($output, 'http://127\.0\.0\.1:\d+')
            if ($match.Success) { $url = $match.Value; break }
        }
    }
    if (-not $url) { throw 'App did not start its localhost server within 30 seconds.' }

    $page = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 15
    # Inspect ASCII identifiers: Windows PowerShell 5.1 may mis-decode UTF-8
    # page text even though browsers honor the HTML charset meta tag.
    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'name="classica-token"' -or
        $page.Content -notmatch 'v2\.4\.1' -or $page.Content -match 'use-edge-session') {
        throw 'First-run UI invalid or contains browser cookie control.'
    }
    $tokenMatch = [regex]::Match($page.Content, 'name="classica-token"\s+content="([^"]+)"')
    if (-not $tokenMatch.Success) { throw 'Missing token in actual localhost UI.' }
    $headers = @{ 'X-Classica-Token' = $tokenMatch.Groups[1].Value }
    $state = Invoke-RestMethod -Uri ($url + '/api/state') -Headers $headers -TimeoutSec 15
    if ($state.version -ne '2.4.1' -or $state.jobs.Count -ne 0) {
        throw 'Version or initial queue state differs from expected fresh install.'
    }
    foreach ($component in @('yt_dlp','yt_dlp_ejs','ffmpeg','ffprobe','deno')) {
        if (-not $state.dependencies.$component) {
            throw "Dependency $component unavailable to running app."
        }
    }

    $payload = '{"urls":["https://www.youtube.com/watch?v=BaW_jenozKc"],"format":"mp3","authorized":true,"use_edge_session":true}'
    $rejected = $false
    try {
        Invoke-WebRequest -UseBasicParsing -Uri ($url + '/api/enqueue') -Method Post -Headers $headers -ContentType 'application/json' -Body $payload -TimeoutSec 10 | Out-Null
    }
    catch [System.Net.WebException] {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 400) {
            $rejected = $true
        }
        else { throw }
    }
    if (-not $rejected) { throw 'Legacy browser-cookie request was not rejected.' }
    $state = Invoke-RestMethod -Uri ($url + '/api/state') -Headers $headers -TimeoutSec 15
    if ($state.jobs.Count -ne 0) {
        throw 'Rejected auth request unexpectedly created a download job.'
    }
    Write-Host 'Fresh ZIP setup, local app startup, API, and no-browser-auth checks: PASS'

    # Native tray, duplicate launch, guided install, stable shortcuts and exit.
    $previousLocalAppData = $env:LOCALAPPDATA
    $env:LOCALAPPDATA = Join-Path $workspace 'isolated-background-profile'
    New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null
    $profileData = Join-Path $env:LOCALAPPDATA 'Classica'
    $hiddenUrl = $null
    $hiddenHeaders = $null
    $native = $null
    $restart = $null
    function Wait-Native($ExpectedDirectory, $Seconds = 60) {
        $deadline = (Get-Date).AddSeconds($Seconds)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 400
            $preparationFailure=$null
            try {
                $record = [IO.File]::ReadAllText((Join-Path $profileData 'instancia.json')) | ConvertFrom-Json
                if ($record.directory -ne $ExpectedDirectory -or $record.version -ne '2.4.1') {
                    $oldState=Invoke-RestMethod -Uri ($record.url+'/api/state') -Headers @{'X-Classica-Token'=$record.token} -TimeoutSec 3
                    if ($oldState.maintenance.phase -eq 'error') { $preparationFailure=$oldState.maintenance.message }
                } else {
                $headers = @{'X-Classica-Token'=$record.token}
                $current = Invoke-RestMethod -Uri ($record.url + '/api/state') -Headers $headers -TimeoutSec 3
                if ($current.version -eq '2.4.1' -and $current.desktop_available) { return $record }
                }
            } catch { }
            if ($preparationFailure) { throw ('Guided installation failed: '+$preparationFailure) }
        }
        throw 'Native controller/server did not become ready.'
    }
    try {
        # Seed real private history without starting a network worker.
        Push-Location -LiteralPath $appDir
        try {
            & $pythonExe -c "import app,pathlib,sys; m=app.Manager(pathlib.Path(sys.argv[1]),start_worker=False); m.set_folder(str(pathlib.Path(sys.argv[1])/'preserved-music')); m.enqueue(['https://www.youtube.com/watch?v=BaW_jenozKc'],'mp3',True); m.cancel(m.jobs[0]['id']); m.stop()" $profileData
            if ($LASTEXITCODE -ne 0) { throw 'Unable to seed isolated history.' }
        } finally { Pop-Location }
        $native = Start-Process -FilePath $launcher -WorkingDirectory $env:RUNNER_TEMP -PassThru
        $instance = Wait-Native $appDir
        if ($native.HasExited) { throw 'Tray controller exited while app was active.' }
        $hiddenUrl=$instance.url; $hiddenHeaders=@{'X-Classica-Token'=$instance.token}
        $originalPid=$instance.pid
        $reopen = Start-Process -FilePath $launcher -WorkingDirectory $env:RUNNER_TEMP -PassThru
        if (-not $reopen.WaitForExit(10000) -or $reopen.ExitCode -ne 0) { throw 'Reopening did not signal the existing tray.' }
        $instance=Wait-Native $appDir
        if ($instance.pid -ne $originalPid) { throw 'Reopening created a duplicate server.' }
        Write-Host 'Tray remains alive and duplicate opening reuses one server: PASS'
        $systemPowerShell=Join-Path ([Environment]::GetFolderPath('System')) 'WindowsPowerShell\v1.0\powershell.exe'
        $helperArguments='-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -ActionId {1}' -f (Join-Path $appDir 'scripts\update_app.ps1'), ('f'*32)
        $invalid=Start-Process -FilePath $systemPowerShell -ArgumentList $helperArguments -Wait -PassThru -WindowStyle Hidden
        if ($invalid.ExitCode -ne 1) { throw 'Maintenance helper accepted an unknown action.' }
        $afterInvalid=Wait-Native $appDir
        if ($afterInvalid.pid -ne $originalPid -or $native.HasExited) { throw 'Rejected maintenance changed the active session.' }
        Write-Host 'Unknown maintenance action is rejected while original remains alive: PASS'

        $diagnostic=Invoke-RestMethod -Uri ($hiddenUrl+'/api/diagnostics') -Headers $hiddenHeaders -TimeoutSec 5
        if ($diagnostic.report -match 'BaW_jenozKc' -or $diagnostic.report.Contains($profileData)) { throw 'Support report leaked private data.' }
        # Install from the exact extracted release. This exercises staging,
        # hash verification, setup before shutdown, new tray, pointer and profile.
        Invoke-RestMethod -Uri ($hiddenUrl+'/api/update/prepare') -Headers $hiddenHeaders -Method Post -ContentType 'application/json' -Body '{"kind":"install"}' -TimeoutSec 10 | Out-Null
        $installedPackage=Join-Path $env:LOCALAPPDATA 'Programs\Classica\versoes\Classica-2.4.1'
        $installedComponents=Join-Path $installedPackage 'Componentes'
        $instance=Wait-Native $installedComponents 600
        $hiddenUrl=$instance.url; $hiddenHeaders=@{'X-Classica-Token'=$instance.token}
        if (-not $native.WaitForExit(30000) -or $native.ExitCode -ne 0) { throw 'Old tray did not finish the guided switch.' }
        $installedState=Invoke-RestMethod -Uri ($hiddenUrl+'/api/state') -Headers $hiddenHeaders -TimeoutSec 5
        if (-not $installedState.maintenance.installed -or $installedState.jobs.Count -ne 1 -or $installedState.jobs[0].status -ne 'cancelled' -or $installedState.folder -ne (Join-Path $profileData 'preserved-music')) { throw 'Guided install did not preserve history/configuration.' }
        $stable=Join-Path $env:LOCALAPPDATA ('Programs\Classica\'+$launcherName)
        $stableCheck=Start-Process -FilePath $stable -ArgumentList '--check' -Wait -PassThru
        if ($stableCheck.ExitCode -ne 0) { throw 'Stable installed launcher failed validation.' }
        $shortcutName='Cl'+[char]0x00E1+'ssica.lnk'
        $shell=New-Object -ComObject WScript.Shell
        foreach ($special in @('DesktopDirectory','Programs')) {
            $shortcutPath=Join-Path ([Environment]::GetFolderPath($special)) $shortcutName
            if (-not (Test-Path -LiteralPath $shortcutPath) -or $shell.CreateShortcut($shortcutPath).TargetPath -ne $stable) { throw 'Installed shortcut missing or wrong target.' }
        }
        if (-not (Test-Path -LiteralPath $launcher)) { throw 'Portable source was changed by installation.' }
        Write-Host 'Guided per-user install, shortcuts, stable launcher and preserved history: PASS'
        # The command signals the same handler as the tray Encerrar menu.
        $exitSignal=Start-Process -FilePath $stable -ArgumentList '--exit' -Wait -PassThru
        if ($exitSignal.ExitCode -ne 0) { throw 'Tray exit signal failed.' }
        $gone=$false
        for ($i=0;$i -lt 40;$i++) { Start-Sleep -Milliseconds 250; try { Invoke-WebRequest -UseBasicParsing -Uri $hiddenUrl -TimeoutSec 2 | Out-Null } catch { $gone=$true;break } }
        if (-not $gone) { throw 'Tray Encerrar did not stop the local server.' }
        Write-Host 'Tray exit stops the owned server: PASS'
        $restart=Start-Process -FilePath $stable -WorkingDirectory $env:RUNNER_TEMP -PassThru
        $instance=Wait-Native $installedComponents
        $hiddenUrl=$instance.url; $hiddenHeaders=@{'X-Classica-Token'=$instance.token}
        Invoke-RestMethod -Uri ($hiddenUrl+'/api/shutdown') -Headers $hiddenHeaders -Method Post -ContentType 'application/json' -Body '{}' -TimeoutSec 10 | Out-Null
        $afterWebExit=Start-Process -FilePath $stable -WorkingDirectory $env:RUNNER_TEMP -PassThru
        $lastInstance=Wait-Native $installedComponents
        if ($lastInstance.pid -eq $instance.pid) { throw 'Immediate reopen after web Sair reused the closing session.' }
        $hiddenUrl=$lastInstance.url; $hiddenHeaders=@{'X-Classica-Token'=$lastInstance.token}
        Invoke-RestMethod -Uri ($hiddenUrl+'/api/shutdown') -Headers $hiddenHeaders -Method Post -ContentType 'application/json' -Body '{}' -TimeoutSec 10 | Out-Null
        Write-Host 'Installed restart and immediate reopen after web Sair: PASS'
    }
    catch {
        foreach ($logName in @('ultimo-lancador.log','ultimo-inicio.log','ultimo-discreto-erros.log')) {
            $logPath=Join-Path $appDir $logName
            if (Test-Path -LiteralPath $logPath) { Write-Host $logName;Get-Content -LiteralPath $logPath -Tail 60 | Write-Host }
        }
        Get-ChildItem -LiteralPath $profileData -Recurse -Filter '*.log' -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_.FullName;Get-Content -LiteralPath $_.FullName -Tail 40 | Write-Host }
        throw
    }
    finally {
        if ($hiddenUrl -and $hiddenHeaders) {
            try { Invoke-RestMethod -Method Post -Uri ($hiddenUrl + '/api/shutdown') -Headers $hiddenHeaders -Body '{}' -ContentType 'application/json' -TimeoutSec 2 | Out-Null } catch { }
        }
        $shortcutName='Cl'+[char]0x00E1+'ssica.lnk'
        $shell=New-Object -ComObject WScript.Shell
        foreach ($special in @('DesktopDirectory','Programs')) {
            $shortcutPath=Join-Path ([Environment]::GetFolderPath($special)) $shortcutName
            if ((Test-Path -LiteralPath $shortcutPath) -and $shell.CreateShortcut($shortcutPath).TargetPath.StartsWith($env:LOCALAPPDATA,[StringComparison]::OrdinalIgnoreCase)) { Remove-Item -LiteralPath $shortcutPath -Force }
        }
        $env:LOCALAPPDATA=$previousLocalAppData
    }
    # Run the media conversion suite FROM THE EXTRACTED ZIP (not the checkout).
    Push-Location -LiteralPath $appDir
    try {
        & $pythonExe -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw 'Bundled media/format regression tests failed.' }
    }
    finally { Pop-Location }
    Write-Host 'Freshly installed ZIP: unit, format and integration tests PASS.'
}
finally {
    if ($serverProcess) {
        try {
            if (-not $serverProcess.HasExited) { Stop-Process -Id $serverProcess.Id -Force -ErrorAction Stop }
        }
        catch { Write-Warning "Unable to stop test server process: $_" }
    }
    # Only an application-specific random folder inside RUNNER_TEMP is deleted.
    if ($workspace.StartsWith($env:RUNNER_TEMP, [StringComparison]::OrdinalIgnoreCase) -and
        $workspace -match 'classica-zip-clean-[0-9a-f]{32}$') {
        Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue
    }
}
