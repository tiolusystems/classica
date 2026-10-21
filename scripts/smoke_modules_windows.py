"""Windows release-contract smoke: install X and Hub without modifying YouTube."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from module_manager import ModuleManager


def main() -> None:
    if os.name != "nt":
        raise RuntimeError("Este teste deve ser executado no Windows.")
    with tempfile.TemporaryDirectory(prefix="classica-modules-") as temp:
        root = Path(temp) / "Programs"
        original = root / "Classica"
        manager = ModuleManager(root=root)
        for name in ("x", "hub"):
            manager._install(name)
            exe = manager.executable(name)
            assert exe and exe.is_file(), f"Não foi possível localizar {name}."
            state = manager.snapshot()["installed"][name]
            assert state["available"] and state["version"], f"Status inválido para {name}."
            assert not state["can_rollback"], "Rollback só deve existir quando houver versão anterior."
        x = manager.executable("x").parent
        assert (x / "_internal" / "ffprobe.exe").is_file()
        assert (x / "_internal" / "ffmpeg.exe").is_file()
        assert (x / "ClassicaXExtractor.exe").is_file()
        assert not original.exists(), "O instalador de módulos não pode alterar o YouTube."
        manager._install("x")  # idempotent; previous user data remains untouched
        assert manager.executable("x").is_file()
        # Verify the production GUI executable X >=1.1.0 starts headless and
        # serves the authenticated iframe session without an extra browser.
        assert tuple(int(p) for p in manager.snapshot()["installed"]["x"]["version"].split(".")) >= (1, 1, 0), "Release X with embedded mode is required"
        manager.begin_embedded_x()
        deadline = time.monotonic() + 35
        embedded = manager.embedded_snapshot()
        while embedded["status"] == "starting" and time.monotonic() < deadline:
            time.sleep(.25)
            embedded = manager.embedded_snapshot()
        assert embedded["status"] == "ready", f"Embedded X did not start: {embedded}"
        assert embedded["url"].startswith("http://127.0.0.1:") and "/?embedded=1#session=" in embedded["url"]
        manager.shutdown()
        assert manager.embedded_snapshot()["url"] is None
        print("Embedded X Windows process/session handshake: PASS")
        print("Module installs from official Releases: PASS")
        print("Versions:", json.dumps(manager.snapshot()["installed"]))


if __name__ == "__main__":
    main()
