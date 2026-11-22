# yt-dlp Web UI

yt-dlp-er jonno ekta shohoj browser UI. Link paste koro, quality / audio / subtitle / thumbnail select koro, download koro. Free, tomar PC te-i chole.

## Install (PowerShell e ei ek line paste koro)
```
irm https://raw.githubusercontent.com/aranashifter/ytdlp-ui/main/install.ps1 | iex
```


Install hobe: `C:\Users\<tomar-naam>\ytdlp-ui`
Prothombar 2-5 min lagbe (yt-dlp, ffmpeg, deno nije download hobe).
Pore chalate: oi folder e `start.bat` double click.

## Update
Same command abar chalao. Tool file gulo notun hobe, tomar Downloads / yt-dlp.exe / ffmpeg ager moto thakbe.

## Muche felte
```
Remove-Item -Recurse -Force "$HOME\ytdlp-ui"
```
Ba folder ta nijer haate delete koro.

## Files
ytdlp_ui.py (server), index.html (UI), start.bat, setup.ps1, install.ps1

Shudhu nijer / anumoti thaka content download koro.
