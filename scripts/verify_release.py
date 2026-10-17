"""Mechanical release checks; not an ISO or WCAG certification."""
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_release import FILES, GENERATED, ROOT


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for name, value in attrs if name == "id")


def luminance(hex_color):
    channels = [int(hex_color[i:i+2], 16)/255 for i in (1, 3, 5)]
    linear = [x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in channels]
    return sum(a*b for a, b in zip(linear, (.2126, .7152, .0722)))


def verify():
    missing = [name for name in FILES if name not in GENERATED and not (ROOT / name).is_file()]
    assert not missing, f"Missing release files: {missing}"
    assert all(".." not in Path(name).parts for name in FILES)
    assert not any("organizar" in name.lower() or "versao_anterior" in name for name in FILES)
    assert "Iniciar discreto.bat" in FILES, "Missing optional background launcher"
    assert "Clássica.exe" in FILES, "Missing branded entry point"
    assert "[switch]$Background" in (ROOT / "iniciar.ps1").read_text(encoding="utf-8"), "Background mode not exposed by launcher"
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    parser = Elements()
    parser.feed(html)
    assert len(parser.ids) == len(set(parser.ids)), "Duplicate HTML IDs"
    assert set(re.findall(r"\$\('([^']+)'\)", js)) <= set(parser.ids), "Missing DOM references"
    assert 'aria-label="by ☧ SYSTEMS"' in html
    assert 'by <span aria-hidden="true">☧</span> SYSTEMS' in html
    assert '>Chi Rho<' not in html and 'PX Systems' not in html
    assert 'name="viewport"' in html and 'user-scalable=no' not in html
    assert 'max="200"' in html
    # The app identity, displayed version and distributed ZIP must always agree.
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    version = re.search(r'^VERSION = "([0-9]+\.[0-9]+\.[0-9]+)"$', app_source, flags=re.MULTILINE)
    assert version is not None, "Missing application version"
    release_filename = "Classica-" + version.group(1) + "-Windows-x64.zip"
    assert release_filename in (ROOT / "scripts/package_release.py").read_text(encoding="utf-8"), "Package version mismatch"
    assert "v" + version.group(1) in html, "Interface version mismatch"
    assert release_filename in (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8"), "Clean install archive version mismatch"
    for foreground, background in [("#172b3a", "#ffffff"), ("#526676", "#ffffff"),
                                   ("#526676", "#f5f7f9"), ("#ffffff", "#0a655e"),
                                   ("#922f22", "#ffffff")]:
        a, b = sorted((luminance(foreground), luminance(background)))
        ratio = (b+.05)/(a+.05)
        assert ratio >= 4.5, f"Insufficient token contrast: {foreground}/{background}: {ratio}"
    lock = json.loads((ROOT / "tools.lock.json").read_text(encoding="utf-8"))
    for tool in lock["windows_x64"]:
        assert re.fullmatch(r"[a-f0-9]{64}", tool["sha256"])
        assert tool["url"].startswith("https://github.com/"+tool["repository"]+"/releases/download/")
        assert tool["tag"] != "latest"
    print(f"Release contract OK: {len(FILES)} files; DOM references, brand, token contrast and tool locks checked.")


if __name__ == "__main__":
    verify()
