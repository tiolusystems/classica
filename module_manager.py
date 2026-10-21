"""Independent, opt-in Windows modules for Clássica. Does not touch the YouTube engine."""
from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import time
from urllib.request import Request
import zipfile

from maintenance import official_open, safe_relative

MODULES = {
    "x": ("tiolusystems/classica-x", "ClassicaX", "ClassicaX.exe"),
    "hub": ("tiolusystems/classica-hub", "ClassicaHub", "ClassicaHub.exe"),
}
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
MAX_FILES = 12000
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def release_metadata(module: str, opener=official_open) -> dict:
    repo, product, _ = MODULES[module]
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    with opener(url) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Os metadados excedem o limite.")
    release = json.loads(raw)
    tag = release.get("tag_name", "")
    version = tag.removeprefix("v")
    if release.get("draft") or release.get("prerelease") or not VERSION.fullmatch(version or "") or tag != "v" + version:
        raise ValueError("Nenhuma versão estável do módulo foi encontrada.")
    filename = f"{product}-{version}-Windows-x64.zip"
    asset = next((a for a in release.get("assets", []) if a.get("name") == filename), None)
    expected_url = f"https://github.com/{repo}/releases/download/{tag}/{filename}"
    if not asset or asset.get("browser_download_url") != expected_url:
        raise ValueError("O arquivo oficial do módulo não está disponível.")
    size, digest = asset.get("size"), asset.get("digest", "")
    if not isinstance(size, int) or not 0 < size <= MAX_ARCHIVE or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("O módulo não possui tamanho e SHA-256 válidos.")
    return {"version": version, "url": expected_url, "sha256": digest.removeprefix("sha256:"), "size": size}


def extract_verified(archive: Path, output: Path, product: str, version: str) -> None:
    prefix = f"{product}-{version}/"
    with zipfile.ZipFile(archive) as package:
        contents = package.infolist()
        if not 1 <= len(contents) <= MAX_FILES or sum(i.file_size for i in contents) > MAX_EXPANDED:
            raise ValueError("Conteúdo do módulo fora dos limites permitidos.")
        seen, verified = set(), []
        for item in contents:
            raw = item.orig_filename
            if not raw.startswith(prefix):
                raise ValueError("O pacote contém arquivos fora do módulo.")
            suffix = raw[len(prefix):].rstrip("/")
            if not suffix:
                continue
            path = safe_relative(suffix)
            key = suffix.casefold()
            if key in seen:
                raise ValueError("O pacote contém nomes duplicados.")
            seen.add(key)
            mode = item.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("O pacote contém um vínculo não permitido.")
            verified.append((item, path))
        for item, rel in verified:
            target = output / rel
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(item) as source, target.open("xb") as destination:
                    shutil.copyfileobj(source, destination, length=256 * 1024)


class ModuleManager:
    def __init__(self, root: Path | None = None, opener=official_open):
        self.root = root or Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local"))) / "Programs"
        self.opener = opener
        self.lock = threading.RLock()
        self.worker: threading.Thread | None = None
        self.state = {"phase": "idle", "message": "", "module": "", "progress": 0}
        self._embedded_process: subprocess.Popen | None = None
        self._embedded_worker: threading.Thread | None = None
        self._embedded_status = "idle"
        self._embedded_url: str | None = None
        self._embedded_error = ""
        self._embedded_stopping = False

    def _folder(self, module: str) -> Path:
        return self.root / MODULES[module][1]

    def _record(self, module: str) -> dict:
        try:
            value = json.loads((self._folder(module) / "current.json").read_text(encoding="utf-8"))
            if isinstance(value, dict):
                return value
        except (OSError, ValueError):
            pass
        return {}

    def executable(self, module: str, version: str | None = None) -> Path | None:
        if module not in MODULES:
            raise ValueError("Módulo desconhecido.")
        ver = version or self._record(module).get("version")
        if not isinstance(ver, str) or not VERSION.fullmatch(ver):
            return None
        product, name = MODULES[module][1:]
        file = self._folder(module) / "versoes" / (product + "-" + ver) / name
        return file if file.is_file() else None

    def snapshot(self) -> dict:
        with self.lock:
            info = dict(self.state)
        info["installed"] = {module: {
            "available": self.executable(module) is not None,
            "version": self._record(module).get("version"),
            "can_rollback": bool(self._record(module).get("previous") and self.executable(module, self._record(module)["previous"])),
        } for module in MODULES}
        info["busy"] = info["phase"] in {"downloading", "verifying", "installing"}
        return info

    def begin(self, module: str) -> dict:
        if module not in ("all", *MODULES):
            raise ValueError("Módulo desconhecido.")
        if os.name != "nt":
            raise ValueError("A instalação guiada dos módulos requer Windows.")
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError("Uma instalação de módulos já está em andamento.")
            self.state = {"phase": "downloading", "module": module, "progress": 0, "message": "Consultando versões oficiais…"}
            self.worker = threading.Thread(target=self._work, args=(module,), daemon=True)
            self.worker.start()
        return self.snapshot()

    def _set(self, **values) -> None:
        with self.lock:
            self.state.update(values)

    def _work(self, module: str) -> None:
        try:
            for kind in (("x", "hub") if module == "all" else (module,)):
                self._install(kind)
            self._set(phase="ready", progress=100, message="Módulos instalados. A central pode ser aberta.")
        except Exception as error:
            self._set(phase="error", message=str(error)[:400], progress=0)

    def _install(self, module: str) -> None:
        repo, product, exe = MODULES[module]
        self._set(phase="downloading", module=module, progress=0,
                  message=f"Obtendo versão oficial de {product}…")
        metadata = release_metadata(module, opener=self.opener)
        base = self._folder(module)
        base.mkdir(parents=True, exist_ok=True)
        versions = base / "versoes"
        versions.mkdir(exist_ok=True)
        target = versions / (product + "-" + metadata["version"])
        if target.exists():
            if self.executable(module, metadata["version"]) != target / exe:
                raise ValueError("Existe uma versão incompleta; nenhum arquivo foi substituído.")
        else:
            with tempfile.TemporaryDirectory(prefix=".classica-", dir=base) as temp:
                staging = Path(temp)
                archive = staging / "download.zip"
                digest = hashlib.sha256()
                size = 0
                with self.opener(metadata["url"]) as response, archive.open("xb") as out:
                    while block := response.read(256 * 1024):
                        size += len(block)
                        if size > metadata["size"] or size > MAX_ARCHIVE:
                            raise ValueError("O arquivo do módulo excedeu o tamanho anunciado.")
                        digest.update(block)
                        out.write(block)
                if size != metadata["size"] or digest.hexdigest() != metadata["sha256"]:
                    raise ValueError("Integridade SHA-256 do módulo inválida. Instalação cancelada.")
                self._set(phase="verifying", progress=75, message="Integridade SHA-256 aprovada. Verificando arquivos…")
                package = staging / "package"
                package.mkdir()
                extract_verified(archive, package, product, metadata["version"])
                if not (package / exe).is_file():
                    raise ValueError("Executável do módulo ausente.")
                if module == "x" and any(not (package / name).is_file() for name in (
                    "ClassicaXExtractor.exe", "_internal/ffmpeg.exe", "_internal/ffprobe.exe"
                )):
                    raise ValueError("Dependências essenciais do X estão ausentes.")
                (package / ".classica-module.json").write_text(
                    json.dumps({"module": module, "version": metadata["version"], "sha256": metadata["sha256"]}),
                    encoding="utf-8",
                )
                self._set(phase="installing", progress=90, message=f"Preparando {product}…")
                package.replace(target)
        previous = self._record(module)
        new = {"version": metadata["version"]}
        if previous.get("version") != metadata["version"] and self.executable(module, previous.get("version")):
            new["previous"] = previous["version"]
        elif previous.get("previous") and self.executable(module, previous.get("previous")):
            new["previous"] = previous["previous"]
        current = base / "current.json"
        temporary = base / "current.tmp"
        temporary.write_text(json.dumps(new), encoding="utf-8")
        temporary.replace(current)
        self._set(progress=95, message=f"{product} instalado em pasta independente.")

    def launch(self, module: str = "hub") -> None:
        executable = self.executable(module)
        if not executable:
            raise ValueError("Instale primeiro a central de módulos.")
        if os.name != "nt":
            raise ValueError("A abertura do aplicativo requer Windows.")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen([str(executable)], cwd=str(executable.parent),
                         creationflags=flags, shell=False)

    def embedded_snapshot(self) -> dict:
        """The UI receives an authenticated, loopback-only iframe address."""
        with self.lock:
            running = self._embedded_process is not None and self._embedded_process.poll() is None
            if self._embedded_status == "ready" and not running:
                self._embedded_status = "error"
                self._embedded_url = None
                self._embedded_error = "O módulo X foi encerrado. Use Abrir X para reabrir."
            return {
                "status": self._embedded_status,
                "url": self._embedded_url if running and self._embedded_status == "ready" else None,
                "error": self._embedded_error,
            }

    def begin_embedded_x(self) -> dict:
        """Start the X engine without a separate browser or Tkinter hub."""
        if os.name != "nt":
            raise ValueError("A interface integrada do X requer Windows.")
        executable = self.executable("x")
        if not executable:
            raise ValueError("Instale o Clássica X para utilizar esta aba.")
        version = self._record("x").get("version", "0.0.0")
        if tuple(map(int, version.split("."))) < (1, 1, 1):
            raise ValueError("Atualize o Clássica X para abrir diretamente nesta aba.")
        with self.lock:
            if self._embedded_stopping:
                raise ValueError("A central está encerrando.")
            if self._embedded_process and self._embedded_process.poll() is None and self._embedded_status == "ready":
                return self.embedded_snapshot()
            if self._embedded_worker and self._embedded_worker.is_alive():
                return self.embedded_snapshot()
            self._embedded_status = "starting"
            self._embedded_url = None
            self._embedded_error = ""
            self._embedded_worker = threading.Thread(target=self._start_embedded_x, args=(executable,), daemon=True)
            self._embedded_worker.start()
        return self.embedded_snapshot()

    def _start_embedded_x(self, executable: Path) -> None:
        process = None
        try:
            base = self._folder("x")
            base.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".classica-tab-", dir=base) as scratch:
                ready = Path(scratch) / "session.json"
                env = os.environ.copy()
                env["CLASSICA_X_EMBED_READY_FILE"] = str(ready)
                env.pop("CLASSICA_X_SMOKE_ALLOW_SYNTHETIC_MEDIA", None)
                process = subprocess.Popen(
                    [str(executable)], cwd=str(executable.parent),
                    env=env, shell=False,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                with self.lock:
                    self._embedded_process = process
                    if self._embedded_stopping:
                        process.terminate()
                        return
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline:
                    with self.lock:
                        if self._embedded_stopping:
                            process.terminate()
                            return
                    if process.poll() is not None:
                        raise RuntimeError("O Clássica X foi encerrado antes de iniciar a interface.")
                    if ready.is_file():
                        record = json.loads(ready.read_text(encoding="utf-8"))
                        port, token = record.get("port"), record.get("session")
                        if not isinstance(port, int) or not 1 <= port <= 65535 or not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", token):
                            raise RuntimeError("Sessão local do X inválida.")
                        # Check the token against the actual local X server. No proxy or remote call.
                        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                        try:
                            connection.request("GET", "/api/state", headers={
                                "Host": f"127.0.0.1:{port}", "X-Classica-Session": token,
                            })
                            response = connection.getresponse()
                            response.read(4096)
                            if response.status != 200:
                                raise RuntimeError("O Clássica X não confirmou a sessão local.")
                        finally:
                            connection.close()
                        with self.lock:
                            if not self._embedded_stopping:
                                self._embedded_url = f"http://127.0.0.1:{port}/?embedded=1#session={token}"
                                self._embedded_status = "ready"
                        return
                    time.sleep(0.15)
                raise TimeoutError("O Clássica X não iniciou a aba dentro do tempo esperado.")
        except Exception as error:
            with self.lock:
                self._embedded_status = "error"
                self._embedded_error = str(error)[:250]
                self._embedded_url = None
            if process and process.poll() is None:
                process.terminate()

    def shutdown(self) -> None:
        """Stop only the X subprocess owned by this shell; do not touch standalone apps."""
        with self.lock:
            self._embedded_stopping = True
            process = self._embedded_process
            worker = self._embedded_worker
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=4)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join(timeout=4)

    def rollback(self, module: str) -> dict:
        if module not in MODULES:
            raise ValueError("Módulo desconhecido.")
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError("Conclua a instalação antes de retornar.")
            record = self._record(module)
            previous = record.get("previous")
            if not previous or not self.executable(module, previous):
                raise ValueError("Não há uma versão anterior disponível.")
            current = self._folder(module) / "current.json"
            temp = current.with_suffix(".tmp")
            temp.write_text(json.dumps({"version": previous, "previous": record["version"]}), encoding="utf-8")
            temp.replace(current)
        return self.snapshot()
