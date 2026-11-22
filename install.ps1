# yt-dlp Web UI - one-line installer / updater
# GitHub e upload korar AGE shudhu nicher line e USER/REPO bodle nijer ta likhun (jemon rahim/ytdlp-ui)
$repo = 'USER/REPO'

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$dest = Join-Path $HOME 'ytdlp-ui'
$tmp  = Join-Path $env:TEMP 'ytdlp-ui-dl'

try {
    if ($repo -eq 'USER/REPO') { throw "install.ps1 e `$repo e nijer GitHub USER/REPO likhun." }
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

    if ($isUpdate) { Write-Host "Update shesh: $dest" -ForegroundColor Green }
    else           { Write-Host "Install shesh: $dest" -ForegroundColor Green }
    Start-Process (Join-Path $dest 'start.bat')
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Repo Public ache kina ar internet check korun." -ForegroundColor Yellow
}
