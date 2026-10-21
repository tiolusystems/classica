"""Independent, opt-in Windows modules for Clássica. Does not touch the YouTube engine."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import threading
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
