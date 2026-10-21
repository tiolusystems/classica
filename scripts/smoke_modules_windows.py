"""Windows release-contract smoke: install X and Hub without modifying YouTube."""
from __future__ import annotations

import json
import os
import sys
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
        print("Module installs from official Releases: PASS")
        print("Versions:", json.dumps(manager.snapshot()["installed"]))


if __name__ == "__main__":
    main()
