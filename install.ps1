# yt-dlp Web UI - one-line installer / updater
# Je folder e PowerShell khulechhen, shei folder er bhitore "ytdlp-ui" nam e folder baniye sob rakhe.
$repo = 'aranashifter/ytdlp-ui'

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$here = (Get-Location).Path
$tmp  = Join-Path $env:TEMP 'ytdlp-ui-dl'

try {
    # 1) already tool er folder er bhitore thakle -> shei folder e update
    if (Test-Path (Join-Path $here 'ytdlp_ui.py')) {
        $dest = $here
    } else {
        # 2) System folder (C:\Windows\System32 etc) hole User folder e, noile ekhon ja folder e achhen shekhane
        $base = if ($here -like "$env:windir*") { $HOME } else { $here }
        $dest = Join-Path $base 'ytdlp-ui'
    }
    $isUpdate = Test-Path (Join-Path $dest 'ytdlp_ui.py')

    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $dest, $tmp | Out-Null

    Write-Host "GitHub theke download hocche: $repo ..." -ForegroundColor Cyan
    Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/main.zip" -OutFile "$tmp\r.zip" -UseBasicParsing
    Expand-Archive "$tmp\r.zip" -DestinationPath "$tmp\x" -Force

    # shudhu repo er file gulo copy hoy; yt-dlp.exe / ffmpeg / Downloads ager moto thake
    Get-ChildItem "$tmp\x" -Directory | Select-Object -First 1 | ForEach-Object {
        Copy-Item "$($_.FullName)\*" $dest -Recurse -Force
    }
    Remove-Item $tmp -Recurse -Force

    if ($isUpdate) { Write-Host "`nUpdate shesh: $dest" -ForegroundColor Green }
    else           { Write-Host "`nInstall shesh: $dest" -ForegroundColor Green }
    Write-Host "Muche felte chaile folder ta delete korun ba: Remove-Item -Recurse -Force `"$dest`"" -ForegroundColor DarkGray
    Start-Process (Join-Path $dest 'start.bat') -WorkingDirectory $dest
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Repo Public ache kina ar internet check korun." -ForegroundColor Yellow
}
