"""Build an allowlisted release; never collect arbitrary workspace files."""
from pathlib import Path
import argparse
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GENERATED = {"Clássica.exe": "build/Clássica.exe"}
PACKAGE_ROOT = "Classica-2.2.1"
USER_FILES = {"Clássica.exe", "Leia-me.txt"}
FILES = (
    "app.py", "features.py", "maintenance.py", "Iniciar.bat", "Iniciar discreto.bat", "Atualizar.bat", "iniciar.ps1", "LICENSE.txt",
    "README.md", "CHANGELOG.md", "SECURITY.md", "THIRD_PARTY.md",
    "requirements.in", "requirements.txt", "requirements.lock", "tools.lock.json",
    "package.json", "package-lock.json", ".gitignore", ".gitattributes",
    "web/index.html", "web/style.css", "web/app.js", "web/favicon.svg", "web/ornament.svg",
    "tests/test_app.py", "tests/test_features.py", "tests/test_maintenance.py", "tests/test_release.py", "tests/test_lifecycle.py", "tests/ui-smoke.mjs",
    "scripts/package_release.py", "scripts/verify_release.py",
    "docs/ARCHITECTURE.md", "docs/BRAND.md", "docs/QUALITY.md", "docs/DEVELOPMENT.md",
    "docs/TRACEABILITY.md", "docs/VALIDATION.md",
    ".github/workflows/quality.yml",
    "assets/classica.ico", "assets/classica.png", "assets/download-windows.svg",
    "launcher/Classica.cs", "launcher/DesktopContext.cs", "scripts/update_app.ps1", "launcher/app.manifest", "scripts/build_launcher.ps1",
    "Clássica.exe", "Leia-me.txt",
)


def source_path(name: str) -> Path:
    generated = ROOT / GENERATED.get(name, name)
    if generated.is_file():
        return generated
    # The test suite also rebuilds FROM the extracted ZIP. Public entry files
    # live one level above Componentes in that layout.
    if name in USER_FILES and ROOT.name == "Componentes":
        return ROOT.parent / name
    return ROOT / name


def archive_path(name: str) -> str:
    return PACKAGE_ROOT + "/" + ("" if name in USER_FILES else "Componentes/") + name


def build(destination: Path) -> tuple[Path, Path]:
    for name, source in GENERATED.items():
        binary = source_path(name)
        if not binary.is_file() or binary.read_bytes()[:2] != b"MZ":
            raise RuntimeError(f"Compile {name} on Windows with scripts/build_launcher.ps1 before packaging.")
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "Classica-2.2.1-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in FILES:
            data = source_path(name).read_bytes()
            if name.endswith((".bat", ".ps1")):
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            info = zipfile.ZipInfo(archive_path(name), date_time=(2026, 10, 17, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            package.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return archive, checksum


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    for path in build(args.output):
        print(path)
