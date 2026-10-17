"""Build an allowlisted release; never collect arbitrary workspace files."""
from pathlib import Path
import argparse
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "app.py", "Iniciar.bat", "Atualizar.bat", "iniciar.ps1", "LICENSE.txt",
    "README.md", "CHANGELOG.md", "SECURITY.md", "THIRD_PARTY.md",
    "requirements.in", "requirements.txt", "requirements.lock", "tools.lock.json",
    "package.json", "package-lock.json", ".gitignore", ".gitattributes",
    "web/index.html", "web/style.css", "web/app.js", "web/favicon.svg",
    "tests/test_app.py", "tests/test_release.py", "tests/ui-smoke.mjs",
    "scripts/package_release.py", "scripts/verify_release.py",
    "docs/ARCHITECTURE.md", "docs/BRAND.md", "docs/QUALITY.md",
    "docs/TRACEABILITY.md", "docs/VALIDATION.md",
    ".github/workflows/quality.yml",
)


def build(destination: Path) -> tuple[Path, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "Classica-2.1.0-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in FILES:
            data = (ROOT / name).read_bytes()
            if name.endswith((".bat", ".ps1")):
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            info = zipfile.ZipInfo("Classica/" + name, date_time=(2026, 10, 17, 0, 0, 0))
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
