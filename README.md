# yt-dlp Web UI

yt-dlp-er jonno ekta shohoj browser UI. Link paste koro, quality / audio / subtitle / thumbnail select koro, download koro. Free, tomar PC te-i chole.

## Install
1. Jekhane rakhte chao shei folder khulo (jemon `D:\Tools`), folder-er address bar e `powershell` likhe Enter dao.
2. Ei ek line paste koro:
```
irm https://raw.githubusercontent.com/aranashifter/ytdlp-ui/main/install.ps1 | iex
```
Oi folder-er bhitore `ytdlp-ui` naam e folder toyri hobe, sob oikhane thakbe (tool, yt-dlp, ffmpeg, deno, Downloads).
Prothombar 2-5 min lagbe. Pore chalate: `ytdlp-ui\start.bat` double click.

## Update
Same folder e PowerShell khule same command abar chalao. Tool file gulo notun hobe, Downloads / yt-dlp.exe / ffmpeg ager moto thakbe.

## Muche felte
`ytdlp-ui` folder ta delete koro. Ba:
```
Remove-Item -Recurse -Force ".\ytdlp-ui"
```

## Developer
**Rakib Al Hasan** - GitHub: [@aranashifter](https://github.com/aranashifter)
Project: https://github.com/aranashifter/ytdlp-ui

Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org).

## Files
ytdlp_ui.py (server), index.html (UI), start.bat, setup.ps1, install.ps1

Shudhu nijer / anumoti thaka content download koro.
