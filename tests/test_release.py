import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import package_release
import verify_release


class ReleaseTests(unittest.TestCase):
    def test_release_contract(self):
        verify_release.verify()

    def test_versioned_artifact_and_ui_agree(self):
        import app
        from html.parser import HTMLParser
        assert app.VERSION == '2.1.1'
        assert f'Classica-{app.VERSION}-Windows-x64.zip' in (ROOT / 'scripts/package_release.py').read_text(encoding='utf-8')
        assert f'v{app.VERSION}' in (ROOT / 'web/index.html').read_text(encoding='utf-8')

    def test_package_is_deterministic_and_contains_only_release_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, checksum = package_release.build(root / "first")
            second, _ = package_release.build(root / "second")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as package:
                self.assertIsNone(package.testzip())
                self.assertIn("Classica/Iniciar discreto.bat", package.namelist())
                self.assertIn(b"-Background", package.read("Classica/Iniciar discreto.bat"))
                self.assertIn(b"[switch]$Background", package.read("Classica/iniciar.ps1"))
                self.assertEqual(set(package.namelist()), {"Classica/"+name for name in package_release.FILES})
                self.assertNotIn(b"Organizar_extracao_antiga", package.read("Classica/README.md"))
            self.assertIn(first.name, checksum.read_text())


if __name__ == "__main__":
    unittest.main()
