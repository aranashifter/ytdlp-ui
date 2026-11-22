#!/usr/bin/env python3
"""
yt-dlp Web UI  -  local only, no pip install needed (Python standard library).
Developed by Rakib Al Hasan (GitHub: @aranashifter) - https://github.com/aranashifter/ytdlp-ui
Put this file, index.html and start.bat in the SAME folder as yt-dlp.exe / ffmpeg.exe
"""
import json, os, re, shlex, shutil, subprocess, sys, threading, queue, time, uuid, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(BASE, "Downloads")
IS_WIN = os.name == "nt"
NOWIN = 0x08000000 if IS_WIN else 0  # CREATE_NO_WINDOW
PORT_START = 8765
BROWSERS = {"chrome", "firefox", "edge", "brave", "opera", "vivaldi", "chromium", "safari"}


def find_ytdlp():
    local = os.path.join(BASE, "yt-dlp.exe" if IS_WIN else "yt-dlp")
    if os.path.isfile(local):
        return local
    return shutil.which("yt-dlp")


YTDLP = find_ytdlp()
HAS_LOCAL_FFMPEG = os.path.isfile(os.path.join(BASE, "ffmpeg.exe" if IS_WIN else "ffmpeg"))
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


# ---------------------------------------------------------------- helpers
def parse_ver(v):
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else None


VERSION = None


def get_version():
    global VERSION
    if YTDLP and VERSION is None:
        try:
            VERSION = run_capture(["--version"], timeout=30)[1].strip() or "?"
        except Exception:
            VERSION = "?"
    return VERSION


def find_js():
    """YouTube needs a JS runtime (deno recommended) for signature / n-challenge solving."""
    for name in ("deno", "node", "bun"):
        exe = name + (".exe" if IS_WIN else "")
        local = os.path.join(BASE, exe)
        p = local if os.path.isfile(local) else shutil.which(name)
        if p:
            return name, p
    return None


def ver_at_least(t):
    v = parse_ver(get_version())
    return bool(v and v >= t)


def common_args(o):
    a = ["--no-colors", "--windows-filenames"]
    if HAS_LOCAL_FFMPEG:
        a += ["--ffmpeg-location", BASE]
    js = find_js()
    if js and ver_at_least((2025, 11, 12)):
        a += ["--js-runtimes", "%s:%s" % js]
        if o.get("remote_ejs"):
            a += ["--remote-components", "ejs:github"]
    ck = (o.get("cookies") or "").lower()
    if ck in BROWSERS:
        a += ["--cookies-from-browser", ck]
    return a


def run_capture(args, timeout=240):
    p = subprocess.run([YTDLP] + args, capture_output=True, timeout=timeout,
                       env=ENV, creationflags=NOWIN, cwd=BASE)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def last_error(err):
    lines = [l for l in err.strip().splitlines() if l.strip()]
    errs = [l for l in lines if "ERROR" in l]
    return (errs or lines or ["Unknown error"])[-1]


def codes(d):
    out = []
    for k, v in (d or {}).items():
        if k == "live_chat":
            continue
        name = k
        if isinstance(v, list) and v and isinstance(v[0], dict):
            name = v[0].get("name") or k
        out.append({"code": k, "name": name})
    return out


# ---------------------------------------------------------------- info
def api_info(d):
    if not YTDLP:
        return {"error": "yt-dlp.exe paoa jacche na. ei folder e yt-dlp.exe rakhun."}
    url = (d.get("url") or "").strip()
    if not url.startswith("http"):
        return {"error": "Valid URL din (http/https)"}
    args = ["-J", "--flat-playlist", "--no-warnings", "--skip-download"] + common_args(d)
    if not d.get("playlist"):
        args.append("--no-playlist")
    args.append(url)
    try:
        rc, out, err = run_capture(args)
    except subprocess.TimeoutExpired:
        return {"error": "Timeout - internet / URL check korun"}
    if rc != 0 or not out.strip():
        return {"error": last_error(err)}
    info = json.loads(out)
    res = {}
    first = info
    if info.get("_type") == "playlist":
        entries = []
        for i, e in enumerate(info.get("entries") or [], 1):
            if not e:
                continue
            entries.append({"index": i, "id": e.get("id"),
                            "title": e.get("title") or e.get("id") or "(untitled)",
                            "duration": e.get("duration"),
                            "url": e.get("url") or e.get("webpage_url")
                                   or ("https://www.youtube.com/watch?v=" + str(e.get("id")))})
        res["playlist"] = {"title": info.get("title"), "count": len(entries), "entries": entries}
        res["title"] = info.get("title")
        res["uploader"] = info.get("uploader") or info.get("channel")
        first = None
        if entries:
            u = entries[0]["url"]
            if not u.startswith("http"):
                u = "https://www.youtube.com/watch?v=" + entries[0]["id"]
            try:
                rc, out, err = run_capture(["-J", "--no-playlist", "--no-warnings"] + common_args(d) + [u])
                if rc == 0 and out.strip():
                    first = json.loads(out)
            except Exception:
                first = None
    if first:
        fmts = first.get("formats") or []
        res["heights"] = sorted({f["height"] for f in fmts
                                 if f.get("height") and f.get("vcodec") not in (None, "none")}, reverse=True)
        langs = {}
        for f in fmts:
            if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none") and f.get("language"):
                note = (f.get("format_note") or "").split(",")[0]
                langs.setdefault(f["language"], note or f["language"])
        res["audio_langs"] = [{"code": k, "name": v} for k, v in langs.items()]
        rows = []
        for f in fmts:
            vc = (f.get("vcodec") or "none").split(".")[0]
            ac = (f.get("acodec") or "none").split(".")[0]
            if (vc == "none" and ac == "none") or f.get("ext") == "mhtml":
                continue
            rows.append({"id": f.get("format_id"), "ext": f.get("ext"), "w": f.get("width"),
                         "h": f.get("height"), "fps": f.get("fps"), "vc": vc, "ac": ac,
                         "tbr": f.get("tbr"), "abr": f.get("abr"),
                         "size": f.get("filesize") or f.get("filesize_approx"),
                         "proto": f.get("protocol"), "lang": f.get("language"),
                         "note": f.get("format_note"), "hdr": f.get("dynamic_range")})
        res["formats"] = rows
        warn = []
        if not res["heights"]:
            warn.append("Kono video format paoa jay nai. Sombhoboto JS runtime (deno) nai ba yt-dlp purano. "
                        "Upore 'Update yt-dlp' chapun ar deno.exe folder e rakhun.")
        elif not find_js():
            warn.append("JS runtime (deno) paoa jay nai, tai kichu high-quality format hoyto dekhachhe na / 403 error dite pare.")
        res["warn"] = warn
        res["subs"] = codes(first.get("subtitles"))
        res["auto_subs"] = codes(first.get("automatic_captions"))
        if "playlist" not in res:
            res["title"] = first.get("title")
            res["uploader"] = first.get("uploader") or first.get("channel")
        res["id"] = first.get("id")
        res["thumbnail"] = first.get("thumbnail")
        res["duration"] = first.get("duration")
    return res


# ---------------------------------------------------------------- command builder
def build_cmd(url, o, pre=None):
    mode = o.get("mode", "video")
    a = [YTDLP, "--newline", "--retries", "10", "--fragment-retries", "10",
                              "--throttled-rate", "100K", "--socket-timeout", "30"] + common_args(o)
    if o.get("playlist"):
        a.append("--ignore-errors")

    h = o.get("height")
    hf = "[height<=%d]" % int(h) if h not in (None, "", "best") else ""
    langs = [l for l in (o.get("audio_langs") or []) if re.fullmatch(r"[A-Za-z0-9_-]+", l)]
    custom = (o.get("custom_format") or "").strip()
    container = o.get("container", "mp4")

    if mode == "audio":
        if custom:
            fmt = custom
        elif langs:
            fmt = "/".join("ba[language^=%s]" % l for l in langs[:1]) + "/ba/b"
        else:
            fmt = "ba/b"
        a += ["-f", fmt, "-x", "--audio-format", o.get("audio_format", "mp3"), "--audio-quality", "0"]
    else:
        if custom:
            fmt = custom
        elif langs:
            aud = "".join("+ba[language^=%s]" % l for l in langs)
            fmt = "bv*%s%s/bv*%s+ba/b%s/b" % (hf, aud, hf, hf)
        else:
            fmt = "bv*%s+ba/b%s/b" % (hf, hf)
        a += ["-f", fmt]
        if custom and custom.count("+") >= 2:
            a.append("--audio-multistreams")
            container = "mkv"
        elif len(langs) > 1 and not custom:
            a.append("--audio-multistreams")
            container = "mkv"
        if o.get("compat") and container == "mp4" and not custom:
            a += ["-S", "res,vcodec:h264,acodec:m4a"]
        a += ["--merge-output-format", container]

    # subtitles
    subs = [c for c in (o.get("subs") or [])]
    auto = [c for c in (o.get("auto_subs") or [])]
    if subs or auto:
        allc = subs + [c for c in auto if c not in subs]
        a += ["--sub-langs", ",".join(allc), "--convert-subs", "srt"]
        if subs:
            a.append("--write-subs")
        if auto:
            a.append("--write-auto-subs")
        if o.get("embed_subs") and mode == "video":
            a.append("--embed-subs")

    # thumbnail
    th = o.get("thumb", "none")
    if th in ("embed", "both"):
        a += ["--embed-thumbnail"]
    if th in ("file", "both"):
        a += ["--write-thumbnail"]
    if th != "none":
        a += ["--convert-thumbnails", "jpg"]

    if o.get("embed_meta", True):
        a.append("--embed-metadata")
    if o.get("chapters"):
        a.append("--embed-chapters")
    if o.get("sponsorblock"):
        a += ["--sponsorblock-remove", "sponsor"]
    if o.get("rate"):
        a += ["-r", str(o["rate"])]
    sec = (o.get("section") or "").strip()
    if sec and re.fullmatch(r"[\d:.]+-([\d:.]+|inf)", sec):
        a += ["--download-sections", "*" + sec]

    # output
    out_dir = os.path.abspath(os.path.expanduser(o.get("dir") or DEFAULT_DIR))
    os.makedirs(out_dir, exist_ok=True)
    if o.get("playlist"):
        a.append("--yes-playlist")
        if o.get("playlist_items"):
            a += ["--playlist-items", str(o["playlist_items"])]
        prefix = "%(playlist_index)03d - " if o.get("number_prefix", True) else ""
        folder = "%(playlist_title).100s/" if o.get("playlist_folder", True) else ""
        tmpl = folder + prefix + "%(title).150s [%(id)s].%(ext)s"
    else:
        a.append("--no-playlist")
        tmpl = "%(title).150s [%(id)s].%(ext)s"
    a += ["-P", out_dir, "-o", tmpl]

    if o.get("extra"):
        a += shlex.split(o["extra"], posix=not IS_WIN)
    if pre:
        a += pre
    a.append(url)
    return a, out_dir


# ---------------------------------------------------------------- jobs
JOBS = []
JOBS_LOCK = threading.Lock()
Q = queue.Queue()
STAGES = {"Merger": "Merging", "ExtractAudio": "Converting audio", "EmbedSubtitle": "Embedding subs",
          "EmbedThumbnail": "Embedding thumbnail", "Metadata": "Writing metadata",
          "ThumbnailsConvertor": "Converting thumbnail", "SubtitlesConvertor": "Converting subs",
          "SponsorBlock": "SponsorBlock", "ModifyChapters": "Chapters", "FixupM4a": "Fixing m4a"}


class Job:
    def __init__(self, url, opts):
        self.id = uuid.uuid4().hex[:8]
        self.url = url
        self.opts = opts
        self.title = (opts or {}).get("title") or url
        self.preset_title = bool((opts or {}).get("title"))
        self.attempt = ""
        self.warn = ""
        self.outfile = ""
        self.status = "queued"
        self.percent = 0.0
        self.speed = ""
        self.eta = ""
        self.item = ""
        self.stage = ""
        self.error = ""
        self.dir = ""
        self.log = []
        self.proc = None
        self.cancelled = False

    def public(self):
        return {"id": self.id, "url": self.url, "title": self.title, "status": self.status,
                "percent": self.percent, "speed": self.speed, "eta": self.eta, "item": self.item,
                "stage": self.stage, "attempt": self.attempt, "warn": self.warn, "outfile": self.outfile, "error": self.error, "dir": self.dir, "log": self.log[-60:]}


def kill_tree(proc):
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, creationflags=NOWIN)
        else:
            proc.terminate()
    except Exception:
        pass


RETRY_MARKS = ("HTTP Error 403", "Requested format is not available", "n challenge", "nsig extraction",
               "Sign in to confirm", "unable to download video data")
MEDIA_EXT = {"mp4", "mkv", "webm", "m4a", "mp3", "opus", "flac", "wav", "mov", "ogg", "aac"}


def attempt_list(o):
    """Different YouTube client / network settings tried one after another when a 403 happens."""
    first = []
    if o.get("client"):
        first = ["--extractor-args", "youtube:player_client=" + o["client"]]
    lst = [first,
           ["--extractor-args", "youtube:player_client=tv,web_safari"],
           ["--extractor-args", "youtube:player_client=mweb,android_vr", "--force-ipv4"]]
    if find_js() and ver_at_least((2025, 11, 12)):
        lst.insert(2, ["--remote-components", "ejs:github"])
    out = []
    for x in lst:  # remove duplicates
        if x not in out:
            out.append(x)
    return out


def run_once(job, cmd):
    """Run one yt-dlp process. Returns (returncode, retryable)."""
    job.log.append("> " + " ".join(cmd))
    job.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", bufsize=1,
                                env=ENV, creationflags=NOWIN, cwd=BASE)
    retryable = False
    err_wait = False
    for line in job.proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        m = re.search(r"\[download\]\s+([\d.]+)%", line)
        if m:
            job.percent = float(m.group(1))
            s_ = re.search(r"at\s+(\S+/s)", line)
            e_ = re.search(r"ETA\s+(\S+)", line)
            job.speed = s_.group(1) if s_ else job.speed
            job.eta = e_.group(1) if e_ else ""
            job.stage = "Downloading"
            if job.percent < 100:
                continue
        m = re.search(r"Downloading item (\d+) of (\d+)", line)
        if m:
            job.item = "%s/%s" % m.groups()
            job.percent = 0
        m = re.search(r"\[download\] Destination: (.+)", line)
        if m and not job.preset_title:
            name = os.path.basename(m.group(1))
            ext = name.rsplit(".", 1)[-1].lower()
            if ext in MEDIA_EXT:
                job.title = re.sub(r"\.f[\w-]+$", "", name.rsplit(".", 1)[0])
        m = re.match(r"\[(\w+)\]", line)
        if m and m.group(1) in STAGES:
            job.stage = STAGES[m.group(1)]
        if line.startswith("ERROR"):
            job.error = line
            err_wait = line.strip() in ("ERROR:", "ERROR")
            if any(k in line for k in RETRY_MARKS):
                retryable = True
        elif err_wait:
            job.error += " " + line
            err_wait = False
            if any(k in line for k in RETRY_MARKS):
                retryable = True
        job.log.append(line)
        if len(job.log) > 500:
            job.log = job.log[-350:]
    job.proc.wait()
    return job.proc.returncode, retryable


def human(b):
    return "%.2f GiB" % (b / 1073741824) if b >= 1073741824 else "%.1f MiB" % (b / 1048576)


def hms(sec):
    sec = int(sec)
    return "%d:%02d:%02d" % (sec // 3600, sec % 3600 // 60, sec % 60)


def job_dir(job):
    return job.dir or os.path.abspath(os.path.expanduser(job.opts.get("dir") or DEFAULT_DIR))


def leftovers(job):
    """All files in the output folder that belong to this video (name contains [video id])."""
    vid = job.opts.get("vid") or ""
    if not re.fullmatch(r"[\w-]{6,20}", vid):
        return []
    tag, d, out = "[%s]" % vid, job_dir(job), []
    try:
        for n in os.listdir(d):
            p = os.path.join(d, n)
            if tag in n and os.path.isfile(p):
                out.append(p)
    except OSError:
        pass
    return out


def is_junk(p):
    return bool(re.search(r"\.temp\.\w+$|\.part$|\.ytdl$|\.f[\w-]+\.\w+$", p))


def ffprobe_duration(path):
    exe = os.path.join(BASE, "ffprobe.exe" if IS_WIN else "ffprobe")
    exe = exe if os.path.isfile(exe) else shutil.which("ffprobe")
    if not exe:
        return "n/a"
    try:
        p = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=nw=1:nk=1", path], capture_output=True, timeout=180, creationflags=NOWIN)
        return float(p.stdout.decode().strip())
    except Exception:
        return None


def finalize(job):
    """After a 'successful' run: make sure the main file really exists and is complete."""
    o = job.opts
    if o.get("playlist") or not o.get("vid"):
        return
    files = leftovers(job)
    junk = [f for f in files if is_junk(f)]
    media = [f for f in files if f.rsplit(".", 1)[-1].lower() in MEDIA_EXT and not is_junk(f)]
    warns = []
    if media:
        main = max(media, key=os.path.getsize)
        job.outfile = "%s (%s)" % (os.path.basename(main), human(os.path.getsize(main)))
        dur = ffprobe_duration(main)
        exp = o.get("duration")
        if dur is None:
            warns.append("Main file play-yogyo noy (corrupt/incomplete). 'Clean & retry' chapun.")
        elif dur != "n/a" and exp and not o.get("section") and dur < float(exp) * 0.97:
            warns.append("File incomplete: duration %s, kintu video %s. 'Clean & retry' chapun." % (hms(dur), hms(exp)))
    else:
        warns.append("Main video file paoa jay nai (merge hoyni). 'Clean & retry' chapun.")
    if junk:
        warns.append("Intermediate/temp file baki ache: " + ", ".join(os.path.basename(f) for f in junk[:3]))
    if warns:
        job.warn = " | ".join(warns)
        job.stage = "Finished (check warning)"


def run_job(job):
    job.status = "running"
    attempts = attempt_list(job.opts)
    for n, extra in enumerate(attempts, 1):
        job.attempt = "try %d/%d" % (n, len(attempts)) if n > 1 else ""
        job.error, job.warn, job.outfile, job.percent, job.speed, job.eta = "", "", "", 0.0, "", ""
        try:
            cmd, job.dir = build_cmd(job.url, job.opts, extra)
        except Exception as e:
            job.status, job.error = "error", "Option error: %s" % e
            return
        if n > 1:
            job.log.append("--- 403 / format error: notun setting diye abar chesta (%d/%d) ---" % (n, len(attempts)))
        try:
            rc, retryable = run_once(job, cmd)
        except Exception as e:
            job.status, job.error = "error", str(e)
            return
        if job.cancelled:
            job.status = "cancelled"
            return
        if rc == 0 and not job.error:
            job.status, job.percent, job.stage, job.speed, job.eta = "done", 100.0, "Finished", "", ""
            finalize(job)
            return
        if rc == 0:
            job.status, job.stage = "done", "Finished (with errors)"
            finalize(job)
            return
        if not retryable:
            break
    job.status = "error"
    job.error = job.error or "yt-dlp exit code %s" % rc
    if "403" in job.error and not find_js():
        job.error += "  |  Poramorsho: deno.exe ei folder e rakhun (README dekhun) ar 'Update yt-dlp' chapun."


def worker():
    while True:
        job = Q.get()
        if job.status == "cancelled":
            continue
        try:
            run_job(job)
        except Exception as e:
            job.status, job.error = "error", str(e)


def api_download(d):
    if not YTDLP:
        return {"error": "yt-dlp.exe paoa jacche na"}
    urls = [u.strip() for u in d.get("urls", []) if u.strip().startswith("http")]
    if not urls:
        return {"error": "Kono valid URL nai"}
    ids = []
    with JOBS_LOCK:
        for u in urls:
            j = Job(u, d.get("options") or {})
            JOBS.append(j)
            Q.put(j)
            ids.append(j.id)
    return {"ok": True, "ids": ids}


def find_job(i):
    return next((j for j in JOBS if j.id == i), None)


def api_cancel(d):
    j = find_job(d.get("id"))
    if not j:
        return {"error": "not found"}
    j.cancelled = True
    if j.status == "queued":
        j.status = "cancelled"
    elif j.proc and j.status == "running":
        kill_tree(j.proc)
    return {"ok": True}


def api_retry(d):
    j = find_job(d.get("id"))
    if not j:
        return {"error": "not found"}
    return api_download({"urls": [j.url], "options": j.opts})


def api_disk(d):
    p = os.path.abspath(os.path.expanduser(d.get("dir") or DEFAULT_DIR))
    while not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return {"free": shutil.disk_usage(p).free, "path": p}


def api_clean_retry(d):
    j = find_job(d.get("id"))
    if not j:
        return {"error": "not found"}
    if j.status in ("queued", "running"):
        return {"error": "Job cholche, age cancel korun"}
    n = 0
    for f in leftovers(j):
        try:
            os.remove(f)
            n += 1
        except OSError:
            pass
    r = api_retry(d)
    r["deleted"] = n
    return r


def api_clear(_):
    with JOBS_LOCK:
        JOBS[:] = [j for j in JOBS if j.status in ("queued", "running")]
    return {"ok": True}


def api_open(d):
    p = os.path.abspath(os.path.expanduser(d.get("dir") or DEFAULT_DIR))
    os.makedirs(p, exist_ok=True)
    if IS_WIN:
        os.startfile(p)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])
    return {"ok": True}


def api_update(d):
    global VERSION
    if not YTDLP:
        return {"error": "yt-dlp not found"}
    args = ["--update-to", "nightly"] if d.get("nightly") else ["-U"]
    rc, out, err = run_capture(args, timeout=300)
    VERSION = None
    return {"output": (out + err).strip()}


def api_config(_):
    js = find_js()
    return {"ytdlp": YTDLP, "version": get_version() if YTDLP else None,
            "ffmpeg": HAS_LOCAL_FFMPEG or bool(shutil.which("ffmpeg")),
            "js": js[0] if js else None, "default_dir": DEFAULT_DIR}


POST_ROUTES = {"/api/info": api_info, "/api/download": api_download, "/api/cancel": api_cancel,
               "/api/clear": api_clear, "/api/retry": api_retry, "/api/disk": api_disk, "/api/clean_retry": api_clean_retry, "/api/open": api_open, "/api/update": api_update}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def host_ok(self):
        return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.host_ok():
            return self.send_json({"error": "forbidden"}, 403)
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(BASE, "index.html"), "rb") as f:
                    body = f.read()
            except OSError:
                body = b"index.html not found next to ytdlp_ui.py"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/jobs":
            with JOBS_LOCK:
                self.send_json([j.public() for j in JOBS])
        elif self.path == "/api/config":
            self.send_json(api_config(None))
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.host_ok() or "application/json" not in self.headers.get("Content-Type", ""):
            return self.send_json({"error": "forbidden"}, 403)
        fn = POST_ROUTES.get(self.path)
        if not fn:
            return self.send_json({"error": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            self.send_json(fn(data))
        except Exception as e:
            self.send_json({"error": str(e)}, 500)


def main():
    threading.Thread(target=worker, daemon=True).start()
    srv = None
    for port in range(PORT_START, PORT_START + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if not srv:
        print("Kono free port paoa jay nai")
        return
    url = "http://127.0.0.1:%d" % srv.server_address[1]
    print("=" * 50)
    print(" yt-dlp Web UI chalu hoyeche:", url)
    print(" Developed by Rakib Al Hasan (@aranashifter)")
    print(" yt-dlp :", YTDLP or "NOT FOUND")
    print(" Ei window bondho korle UI bondho hoye jabe.")
    print("=" * 50)
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
