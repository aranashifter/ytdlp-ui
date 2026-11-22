# yt-dlp Web UI - auto setup (yt-dlp, ffmpeg, deno, python check)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Set-Location $PSScriptRoot

function Get-File($url, $out) {
    Write-Host "  Downloading $out ..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
}

function Has-Python {
    foreach ($c in 'py', 'python') {
        $x = Get-Command $c -ErrorAction SilentlyContinue
        if ($x -and $x.Source -notlike '*WindowsApps*') { return $true }
    }
    return $false
}

try {
    Write-Host "`n=== yt-dlp Web UI setup ===" -ForegroundColor Green

    if (-not (Test-Path 'yt-dlp.exe')) {
        Get-File 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' 'yt-dlp.exe'
    }

    if (-not ((Test-Path 'ffmpeg.exe') -and (Test-Path 'ffprobe.exe'))) {
        Get-File 'https://github.com/yt-dlp/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip' 'ffmpeg.zip'
        Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'ffmpeg_tmp' -Force
        Get-ChildItem 'ffmpeg_tmp' -Recurse -Include 'ffmpeg.exe', 'ffprobe.exe' | Copy-Item -Destination '.' -Force
        Remove-Item 'ffmpeg_tmp' -Recurse -Force
        Remove-Item 'ffmpeg.zip' -Force
    }

    if (-not (Test-Path 'deno.exe')) {
        Get-File 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip' 'deno.zip'
        Expand-Archive -Path 'deno.zip' -DestinationPath '.' -Force
        Remove-Item 'deno.zip' -Force
    }

    if (-not (Has-Python)) {
        Write-Host "  Python paoa jay nai, install kora hocche..." -ForegroundColor Yellow
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
            Write-Host "`nPython install hoyeche. Ei window bondho kore start.bat ABAR chalan." -ForegroundColor Green
        } else {
            Start-Process 'https://www.python.org/downloads/'
            Write-Host "`nPython download page khulechhe. Install korar somoy 'Add python.exe to PATH' tick din, tarpor start.bat abar chalan." -ForegroundColor Yellow
        }
        exit 2
    }

    Write-Host "`nSetup shesh!" -ForegroundColor Green
} catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Internet connection check kore start.bat abar chalan." -ForegroundColor Yellow
    exit 1
}
