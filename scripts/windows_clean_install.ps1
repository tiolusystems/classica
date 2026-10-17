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

$workspace = Join-Path $env:RUNNER_TEMP ('classica-zip-clean-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
$serverProcess = $null
try {
    Expand-Archive -LiteralPath $archivePath -DestinationPath $workspace
    $appDir = Join-Path $workspace 'Classica'
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
        & $pythonExe -c "import app,pathlib; assert pathlib.Path(app.__file__).resolve().parent == pathlib.Path.cwd(); assert app.VERSION == '2.1.0'; assert all(app.dependencies().values()), app.dependencies(); print('Fresh runtime components: PASS')"
        if ($LASTEXITCODE -ne 0) { throw 'Fresh runtime import/dependencies check failed.' }
    }
    finally { Pop-Location }

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
            $output = Get-Content -LiteralPath $stdout -Raw
            $match = [regex]::Match($output, 'http://127\.0\.0\.1:\d+')
            if ($match.Success) { $url = $match.Value; break }
        }
    }
    if (-not $url) { throw 'App did not start its localhost server within 30 seconds.' }

    $page = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 15
    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'Clássica' -or
        $page.Content -match 'use-edge-session') {
        throw 'First-run UI invalid or contains browser cookie control.'
    }
    $tokenMatch = [regex]::Match($page.Content, 'name="classica-token"\s+content="([^"]+)"')
    if (-not $tokenMatch.Success) { throw 'Missing token in actual localhost UI.' }
    $headers = @{ 'X-Classica-Token' = $tokenMatch.Groups[1].Value }
    $state = Invoke-RestMethod -Uri ($url + '/api/state') -Headers $headers -TimeoutSec 15
    if ($state.version -ne '2.1.0' -or $state.jobs.Count -ne 0) {
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
