# /// script
# requires-python = ">=3.11"
# dependencies = ["yt-dlp[default]"]
# ///
"""Clássica: fila local de áudio e vídeo do YouTube. Execute pelo Iniciar.bat."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit, quote
import uuid
import webbrowser

ROOT = Path(__file__).resolve().parent
VERSION = "2.1.0"
FORMATS = {"mp3": "MP3 · 320 kbps", "m4a": "M4A · AAC", "aac": "AAC",
           "wav": "WAV", "flac": "FLAC", "ogg": "OGG · Vorbis", "opus": "OPUS",
           "original": "Áudio original"}
VIDEO_FORMATS = {"mp4": "MP4", "mkv": "MKV", "webm": "WebM"}
RESOLUTIONS = {"best", "2160", "1440", "1080", "720", "480"}
ACTIVE = {"preparing", "downloading", "converting"}
TERMINAL = {"done", "error", "cancelled", "interrupted"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
RATE_LIMIT_WAIT = 60


def canonical_url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Link inválido.")
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"https", "http"} or parsed.username or parsed.password:
        raise ValueError("Use um link completo do YouTube, iniciado por https://.")
    try:
        if parsed.port not in (None, 80, 443):
            raise ValueError("Porta não permitida no link.")
    except ValueError:
        raise ValueError("Endereço do YouTube inválido.") from None
    host = (parsed.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        video = parsed.path.strip("/")
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        parts = parsed.path.strip("/").split("/")
        if parsed.path.rstrip("/") == "/watch":
            video = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
            video = parts[1]
        else:
            raise ValueError("Cole o link de um vídeo. Para vários downloads, use um link por linha.")
    else:
        raise ValueError("Somente links de vídeos do YouTube são aceitos.")
    if not VIDEO_ID.fullmatch(video):
        raise ValueError("Não foi possível identificar o vídeo neste link.")
    return "https://www.youtube.com/watch?v=" + video


def dependencies() -> dict:
    return {"yt_dlp": importlib.util.find_spec("yt_dlp") is not None,
            "yt_dlp_ejs": importlib.util.find_spec("yt_dlp_ejs") is not None,
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "ffprobe": bool(shutil.which("ffprobe")),
            "deno": bool(shutil.which("deno"))}


def video_selector(resolution: str) -> str:
    limit = "" if resolution == "best" else f"[height<={int(resolution)}]"
    return f"bv*{limit}+ba/b{limit}"


def command_for(job: dict) -> list[str]:
    # A list of arguments avoids shell interpretation of titles, paths and URLs.
    cmd = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist",
           "--no-colors", "--no-quiet", "--newline", "--windows-filenames", "--no-overwrites",
           "--socket-timeout", "30", "--retries", "2", "--fragment-retries", "2",
           "--extractor-retries", "0", "--sleep-requests", "1",
           "--sleep-interval", "5", "--max-sleep-interval", "10",
           "--retry-sleep", "http:exp=2:10", "--concurrent-fragments", "1"]
    # Fixed browser only: never accept a profile path or arbitrary extractor args.
    if job.get("use_edge_session") is True:
        cmd += ["--cookies-from-browser", "edge:Default", "--no-cache-dir"]
    output = "%(title).140B [%(id)s].%(ext)s"
    if job["format"] in VIDEO_FORMATS:
        resolution = job.get("resolution", "best")
        label = "melhor" if resolution == "best" else resolution + "p"
        output = f'%(title).120B [%(id)s] [video-{job["format"]}-{label}].%(ext)s'
    cmd += ["--progress", "--progress-delta", "0.5", "--progress-template",
            'download:CLASSICA_PROGRESS:%(progress)j',
            "--print", "before_dl:CLASSICA_TITLE:%(title)s", "--print",
            "after_move:CLASSICA_FILE:%(filepath)s", "--no-simulate",
            "-P", job["folder"], "-o", output]
    deno = shutil.which("deno")
    if deno:
        cmd += ["--js-runtimes", "deno:" + deno]
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd += ["--ffmpeg-location", str(Path(ffmpeg).parent)]
    if job["format"] in VIDEO_FORMATS:
        cmd += ["-f", video_selector(job.get("resolution", "best")), "--merge-output-format", "mkv"]
        if job["format"] == "webm":
            cmd += ["--recode-video", "webm", "--postprocessor-args",
                    "VideoConvertor+ffmpeg_o:-c:v libvpx-vp9 -crf 32 -b:v 0 -c:a libopus"]
        else:
            cmd += ["--remux-video", job["format"]]
        cmd += ["--embed-metadata"]
    elif job["format"] == "original":
        cmd += ["-f", "bestaudio"]
    else:
        cmd += ["-f", "bestaudio/best", "-x", "--audio-format", "vorbis" if job["format"] == "ogg" else job["format"],
                "--audio-quality", "320K" if job["format"] in {"mp3", "m4a", "aac"} else "0"]
        # yt-dlp extracts AAC into an M4A container. Remux, without re-encoding,
        # when the user explicitly requests a raw .aac file.
        if job["format"] == "aac":
            cmd += ["--remux-video", "aac"]
        else:
            cmd += ["--embed-metadata"]
    cmd += ["--", job["url"]]
    return cmd


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass


def friendly_error(log: str) -> str:
    text = log.lower()
    if any(marker in text for marker in ("failed to decrypt", "dpapi", "cookie database", "cookies database", "could not find edge cookies", "failed to load cookies")):
        return "Não foi possível ler a sessão do Edge. Se houver bloqueio do banco de cookies, feche todas as janelas do Edge e tente uma vez. Se houver falha de descriptografia/DPAPI, a proteção do Windows pode impedir a leitura. Não desative proteções, não execute como administrador nem instale extensões para contorná-la. Desmarque Usar minha sessão do Edge para continuar sem sessão."
    if "certificate_verify_failed" in text or "certificate verify failed" in text:
        return "A conexão segura com o YouTube falhou. Confira a data e a hora do Windows e os certificados da sua rede. Em uma rede administrada, solicite apoio de TI."
    if (rate_limited(log) or "sign in" in text or "not a bot" in text):
        return "O YouTube limitou as requisições ou pediu uma verificação. Pare as tentativas e confira o vídeo no Edge. Se funcionar com sua conta, você pode autorizar Usar minha sessão do Edge e tentar uma vez mais tarde. Atualizar.bat pode corrigir incompatibilidades, mas não garante resolver HTTP 429, login ou PO Token. A aplicação não contorna CAPTCHA, DRM ou pagamento."
    if "requested format is not available" in text:
        return "O formato ou a resolução solicitada não está disponível nesta tentativa. Escolha Melhor disponível para vídeo. Isso também pode ocorrer quando o YouTube não libera os formatos ao extrator."
    if "po token" in text or "po_token" in text or "visitor data" in text:
        return "O YouTube não forneceu os dados de sessão ou o PO Token exigido nesta tentativa. Atualizar.bat pode corrigir incompatibilidades. Se persistir, aguarde e confira o vídeo no navegador; a sessão opcional do Edge não garante resolver essa exigência."
    if "private video" in text or "video unavailable" in text or "video has been removed" in text:
        return "Vídeo indisponível, privado ou removido. Confira o link no YouTube."
    if "403" in text or "nsig" in text or "javascript" in text:
        return "O YouTube recusou a extração. Feche a aplicação, execute Atualizar.bat e tente novamente."
    if "disk" in text or "space" in text or "permission" in text:
        return "Não foi possível gravar o arquivo. Confira o espaço livre e a permissão da pasta."
    if "timed out" in text or "resolve" in text or "connection" in text:
        return "Falha de conexão. Confira sua internet e tente novamente."
    errors = [x.removeprefix("ERROR: ").strip() for x in log.splitlines() if "ERROR:" in x]
    return (errors[-1][:500] if errors else "O download não foi concluído. Veja os detalhes e tente novamente.")


def rate_limited(log: str) -> bool:
    return bool(re.search(r"\b429\b|too many requests", log, re.I))


def verify_media(job: dict) -> None:
    """Do not mistake an HTML error page, empty file or silent video for success."""
    file = Path(job["file"]).resolve()
    if not file.is_relative_to(Path(job["folder"]).resolve()) or not file.is_file() or file.stat().st_size == 0:
        raise ValueError("O arquivo final não está disponível na pasta de destino.")
    kwargs = dict(capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error",
                                 "-show_entries", "stream=codec_type,codec_name", "-of", "json", str(file)], **kwargs)
        streams = json.loads(result.stdout).get("streams", []) if result.returncode == 0 else []
        kinds = {stream.get("codec_type") for stream in streams if stream.get("codec_name") not in (None, "unknown")}
    except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Não foi possível validar o arquivo recebido. Confira a conexão e os componentes da aplicação.") from exc
    if "audio" not in kinds or (job["format"] in VIDEO_FORMATS and "video" not in kinds):
        raise ValueError("O arquivo recebido não contém o áudio/vídeo esperado. Ele pode ser uma resposta de erro da rede. Não foi marcado como concluído; consulte os detalhes e tente novamente mais tarde.")


class Manager:
    def __init__(self, data_dir: Path, start_worker=True):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "historico.json"
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.process = None
        self.current_id = None
        self.folder = str(Path.home() / "Music" / "Classica")
        self.jobs = []
        self.queue_pause = {"until": 0, "manual": False, "reason": ""}
        self.load()
        if start_worker:
            self.worker = threading.Thread(target=self.run, daemon=True)
            self.worker.start()

    def load(self):
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.folder = payload["folder"]
            self.jobs = payload["jobs"][-500:]
            self.queue_pause = payload.get("queue_pause", self.queue_pause)
            for job in self.jobs:
                # Consent must be renewed after restarting, including for retries.
                job["use_edge_session"] = False
                if job["status"] in ACTIVE | {"queued"}:
                    job.update(status="interrupted", error="A sessão foi encerrada. Use Tentar novamente para continuar.")
        except FileNotFoundError:
            pass
        except (ValueError, KeyError, TypeError):
            # Preserve a damaged file for recovery rather than silently overwriting it.
            shutil.copy2(self.state_file, self.data_dir / ("historico-recuperacao-" + str(int(time.time())) + ".json"))
            self.jobs = []

    def save(self):
        # Caller holds self.lock. Atomic replacement prevents partial JSON on interruption.
        temp = self.state_file.with_suffix(".tmp")
        jobs = [{k: v for k, v in job.items() if k != "use_edge_session"} for job in self.jobs]
        temp.write_text(json.dumps({"folder": self.folder, "jobs": jobs, "queue_pause": self.queue_pause}, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, self.state_file)

    def snapshot(self):
        with self.lock:
            return {"version": VERSION, "folder": self.folder, "jobs": copy.deepcopy(self.jobs),
                    "queue_pause": copy.deepcopy(self.queue_pause), "dependencies": dependencies()}

    def find(self, job_id):
        for job in self.jobs:
            if job["id"] == job_id:
                return job
        raise ValueError("Download não encontrado.")

    def set_folder(self, folder):
        if not isinstance(folder, str) or not folder.strip():
            raise ValueError("Informe uma pasta de destino.")
        path = Path(folder).expanduser()
        if not path.is_absolute():
            raise ValueError("Informe o caminho completo da pasta.")
        path.mkdir(parents=True, exist_ok=True)
        probe = path / (".classica-" + uuid.uuid4().hex)
        try:
            probe.write_bytes(b"")
        finally:
            probe.unlink(missing_ok=True)
        with self.lock:
            self.folder = str(path.resolve())
            self.save()

    def enqueue(self, urls, format_, authorized, resolution="best", use_edge_session=False):
        if type(use_edge_session) is not bool:
            raise ValueError("A autorização para usar a sessão do Edge deve ser verdadeira ou falsa.")
        if authorized is not True:
            raise ValueError("Confirme que possui autorização para baixar as gravações.")
        if format_ not in FORMATS and format_ not in VIDEO_FORMATS:
            raise ValueError("Formato de download inválido.")
        if not isinstance(resolution, str) or resolution not in RESOLUTIONS:
            raise ValueError("Resolução de vídeo inválida.")
        resolution = resolution if format_ in VIDEO_FORMATS else "best"
        if not isinstance(urls, list) or not 1 <= len(urls) <= 50:
            raise ValueError("Adicione de 1 a 50 links por vez.")
        canonical = list(dict.fromkeys(canonical_url(url) for url in urls))
        with self.lock:
            pending = sum(j["status"] not in TERMINAL for j in self.jobs)
            if pending + len(canonical) > 100:
                raise ValueError("A fila comporta até 100 downloads pendentes.")
            Path(self.folder).mkdir(parents=True, exist_ok=True)
            added, skipped = [], 0
            for url in canonical:
                if any(j["url"] == url and j["format"] == format_ and j.get("resolution", "best") == resolution and j["status"] not in TERMINAL for j in self.jobs):
                    skipped += 1
                    continue
                job = dict(id=uuid.uuid4().hex, url=url, format=format_, folder=self.folder, resolution=resolution,
                           title="Aguardando informações do vídeo", status="queued", progress=0,
                           speed="", eta="", error="", log="", file="", created=time.time(), authorized=True,
                           use_edge_session=use_edge_session, auto_retry_count=0)
                self.jobs.append(job)
                added.append(job["id"])
            # Bound history without dropping active jobs.
            excess = len(self.jobs) - 500
            if excess > 0:
                remove = {j["id"] for j in self.jobs if j["status"] in TERMINAL}
                for old in list(self.jobs):
                    if excess <= 0:
                        break
                    if old["id"] in remove:
                        self.jobs.remove(old)
                        excess -= 1
            self.save()
        self.wake.set()
        return {"added": len(added), "skipped": skipped}

    def cancel(self, job_id):
        with self.lock:
            job = self.find(job_id)
            if job["status"] in TERMINAL:
                return
            job["status"] = "cancelled"
            if self.current_id == job_id and self.process:
                terminate_process(self.process)
            self.save()

    def retry(self, job_id, use_edge_session=False):
        if type(use_edge_session) is not bool:
            raise ValueError("A autorização para usar a sessão do Edge deve ser verdadeira ou falsa.")
        with self.lock:
            self.check_cooldown()
            job = self.find(job_id)
            if job["status"] not in {"error", "cancelled", "interrupted"}:
                raise ValueError("Este item não precisa ser reiniciado.")
            job.update(status="queued", progress=0, error="", log="", speed="", eta="", file="", use_edge_session=use_edge_session, auto_retry_count=0)
            self.queue_pause = {"until": 0, "manual": False, "reason": ""}
            self.save()
        self.wake.set()

    def check_cooldown(self):
        remaining = self.queue_pause["until"] - time.time()
        if remaining > 0:
            raise ValueError(f"O YouTube limitou as requisições. Aguarde mais {int(remaining) + 1} segundos antes de retomar.")

    def resume(self):
        with self.lock:
            self.check_cooldown()
            self.queue_pause = {"until": 0, "manual": False, "reason": ""}
            self.save()
        self.wake.set()

    def record_failure(self, job):
        job.update(status="error", error=friendly_error(job["log"]), speed="", eta="")
        if rate_limited(job["log"]):
            repeat = job.get("auto_retry_count", 0) == 0
            self.queue_pause = {"until": time.time() + RATE_LIMIT_WAIT, "manual": not repeat,
                                "reason": "O YouTube respondeu HTTP 429. A fila foi pausada para reduzir novas requisições."}
            if repeat:
                job.update(status="queued", auto_retry_count=1, file="", progress=0,
                           error="HTTP 429: aguardando uma pausa de 60 segundos antes de uma única nova tentativa automática.")

    def clear(self):
        with self.lock:
            self.jobs = [j for j in self.jobs if j["status"] not in TERMINAL]
            self.save()

    def parse_line(self, job, line):
        if line.startswith("CLASSICA_PROGRESS:"):
            try:
                p = json.loads(line.split(":", 1)[1])
                total = p.get("total_bytes") or p.get("total_bytes_estimate")
                downloaded = p.get("downloaded_bytes") or 0
                job["progress"] = min(99.5, downloaded * 100 / total) if total else 0
                job["status"] = "converting" if p.get("status") == "finished" else "downloading"
                job["speed"] = ((f'{p["speed"] / 1024 / 1024:.1f} MB/s') if p.get("speed") else "")
                job["eta"] = str(int(p["eta"])) + " s" if p.get("eta") is not None else ""
            except (ValueError, TypeError, KeyError):
                pass
        elif line.startswith("CLASSICA_TITLE:"):
            job["title"] = line.split(":", 1)[1].strip()[:500]
        elif line.startswith("CLASSICA_FILE:"):
            path = Path(line.split(":", 1)[1].strip()).resolve()
            if path.is_relative_to(Path(job["folder"]).resolve()) and path.is_file():
                job["file"] = str(path)
        elif line.startswith(("[ExtractAudio]", "[Metadata]", "[Merger]", "[VideoRemuxer]", "[VideoConvertor]")):
            job["status"] = "converting"

    def run(self):
        while not self.stopping.is_set():
            self.wake.wait(0.5)
            self.wake.clear()
            with self.lock:
                if self.queue_pause["manual"] or time.time() < self.queue_pause["until"]:
                    continue
                if self.queue_pause["reason"]:
                    self.queue_pause = {"until": 0, "manual": False, "reason": ""}
                job = next((j for j in self.jobs if j["status"] == "queued"), None)
                if not job:
                    continue
                job.update(status="preparing", error="", log="", file="")
                self.current_id = job["id"]
                self.save()
            try:
                missing = [key for key, value in dependencies().items() if not value]
                if missing:
                    raise RuntimeError("Componentes ausentes: " + ", ".join(missing) + ". Feche a aplicação e execute Iniciar.bat.")
                kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace", bufsize=1)
                if os.name == "nt":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
                else:
                    kwargs["start_new_session"] = True
                with self.lock:
                    if job["status"] == "cancelled" or self.stopping.is_set():
                        continue
                    self.process = subprocess.Popen(command_for(job), **kwargs)
                    process = self.process
                with process.stdout:
                    for line in process.stdout:
                        with self.lock:
                            if job["status"] == "cancelled" or self.stopping.is_set():
                                continue
                            clean = line.rstrip()
                            job["log"] = (job["log"] + clean + "\n")[-10000:]
                            self.parse_line(job, clean)
                code = process.wait()
                if code == 0 and job["status"] != "cancelled" and not self.stopping.is_set() and job["file"]:
                    verify_media(job)
                with self.lock:
                    if job["status"] == "cancelled":
                        pass
                    elif self.stopping.is_set():
                        job.update(status="interrupted", error="Aplicação encerrada. Use Tentar novamente para continuar.")
                    elif code == 0 and job["file"] and Path(job["file"]).is_file():
                        job.update(status="done", progress=100, speed="", eta="")
                    else:
                        self.record_failure(job)
            except Exception as exc:
                with self.lock:
                    if job["status"] != "cancelled":
                        job.update(status="error", error=str(exc)[:700])
            finally:
                with self.lock:
                    self.process = None
                    self.current_id = None
                    self.save()

    def stop(self):
        self.stopping.set()
        self.wake.set()
        with self.lock:
            if self.process:
                terminate_process(self.process)
        worker = getattr(self, "worker", None)
        if worker and worker is not threading.current_thread():
            worker.join(timeout=12)
        with self.lock:
            for job in self.jobs:
                if job["status"] in ACTIVE | {"queued"}:
                    job.update(status="interrupted", error="Sessão encerrada. Use Tentar novamente para continuar.")
            self.save()


class Handler(BaseHTTPRequestHandler):
    server_version = "Classica/" + VERSION

    def log_message(self, *_):
        pass

    def valid_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def respond(self, status, payload, mime="application/json; charset=utf-8"):
        body = json.dumps(payload, ensure_ascii=False).encode() if not isinstance(payload, bytes) else payload
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Classica-Version", VERSION)
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.valid_host():
            self.respond(403, {"error": "Acesso local inválido."})
            return
        path = urlsplit(self.path).path
        if path == "/":
            self.respond(200, (ROOT / "web" / "index.html").read_bytes().replace(b"__TOKEN__", self.server.token.encode()), "text/html; charset=utf-8")
        elif path in {"/app.js", "/style.css", "/favicon.svg"}:
            mime = {"/app.js": "application/javascript; charset=utf-8", "/style.css": "text/css; charset=utf-8", "/favicon.svg": "image/svg+xml"}[path]
            self.respond(200, (ROOT / "web" / path[1:]).read_bytes(), mime)
        elif path == "/api/state":
            if self.headers.get("X-Classica-Token") != self.server.token:
                self.respond(403, {"error": "Sessão inválida. Reabra a aplicação."})
            else:
                self.respond(200, self.server.manager.snapshot())
        elif path.startswith("/file/"):
            try:
                with self.server.manager.lock:
                    job = copy.deepcopy(self.server.manager.find(path.split("/")[-1]))
                file = Path(job["file"])
                if job["status"] != "done" or not file.is_file() or not file.resolve().is_relative_to(Path(job["folder"]).resolve()):
                    raise ValueError("Arquivo não disponível. Confira a pasta de destino.")
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(file.stat().st_size))
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(file.name))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                with file.open("rb") as stream:
                    shutil.copyfileobj(stream, self.wfile)
            except (ValueError, OSError) as exc:
                self.respond(404, {"error": str(exc)})
        else:
            self.respond(404, {"error": "Página não encontrada."})

    def do_POST(self):
        if not self.valid_host() or self.headers.get("X-Classica-Token") != self.server.token:
            self.respond(403, {"error": "Sessão inválida. Reabra a aplicação."})
            return
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
            self.respond(403, {"error": "Origem inválida."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 131072:
                raise ValueError("Solicitação muito grande.")
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Solicitação inválida.")
            path = urlsplit(self.path).path
            manager = self.server.manager
            result = {"ok": True}
            if path == "/api/enqueue":
                result = manager.enqueue(data.get("urls"), data.get("format"), data.get("authorized"), data.get("resolution", "best"), data.get("use_edge_session", False))
            elif path == "/api/cancel":
                manager.cancel(data.get("id"))
            elif path == "/api/retry":
                manager.retry(data.get("id"), data.get("use_edge_session", False))
            elif path == "/api/clear":
                manager.clear()
            elif path == "/api/resume":
                manager.resume()
            elif path == "/api/folder":
                manager.set_folder(data.get("folder"))
            elif path == "/api/open-folder":
                folder = manager.folder
                Path(folder).mkdir(parents=True, exist_ok=True)
                if os.name == "nt":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["xdg-open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif path == "/api/shutdown":
                self.respond(200, result)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            else:
                self.respond(404, {"error": "Operação não encontrada."})
                return
            self.respond(200, result)
        except (ValueError, OSError, TypeError) as exc:
            self.respond(400, {"error": str(exc)[:700]})


def create_server(manager, port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.manager = manager
    server.token = secrets.token_urlsafe(32)
    return server


def main():
    parser = argparse.ArgumentParser(description="Clássica — downloads locais de áudio e vídeo")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    data_dir = args.data_dir or Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "Classica"
    # OS-level advisory lock prevents two sessions from overwriting queue history.
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_file = (data_dir / "sessao.lock").open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("A Clássica já está aberta. Use a janela existente ou encerre-a antes de abrir novamente.")
        return 1
    manager = Manager(data_dir)
    server = create_server(manager, args.port)
    url = f"http://127.0.0.1:{server.server_port}"
    print("\nCLÁSSICA — áudio e vídeo · by ☧ SYSTEMS\n")
    print("Abra no navegador: " + url)
    print("Mantenha esta janela aberta. Para encerrar, use o botão Sair ou Ctrl+C.\n", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
        server.server_close()
        lock_file.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
