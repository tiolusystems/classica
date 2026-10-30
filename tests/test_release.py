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
        assert app.VERSION == '2.4.1'
        assert f'Classica-{app.VERSION}-Windows-x64.zip' in (ROOT / 'scripts/package_release.py').read_text(encoding='utf-8')
        assert f'v{app.VERSION}' in (ROOT / 'web/index.html').read_text(encoding='utf-8')

    def test_package_is_deterministic_and_contains_only_release_files(self):
        if not package_release.source_path('Clássica.exe').is_file():
            self.skipTest('Native Windows launcher is compiled and packaged by Windows CI')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, checksum = package_release.build(root / "first")
            second, _ = package_release.build(root / "second")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as package:
                prefix = package_release.PACKAGE_ROOT + '/Componentes/'
                entry = package_release.PACKAGE_ROOT + '/'
                self.assertIsNone(package.testzip())
                self.assertTrue(package.read(entry+'Clássica.exe').startswith(b'MZ'))
                top = {name[len(entry):].split('/')[0] for name in package.namelist()}
                self.assertEqual(top, {'Clássica.exe', 'Leia-me.txt', 'Componentes'})
                self.assertIn(prefix+'assets/classica.ico', package.namelist())
                self.assertIn(prefix+"Iniciar discreto.bat", package.namelist())
                self.assertIn(b"-Background", package.read(prefix+"Iniciar discreto.bat"))
                self.assertIn(b"[switch]$Background", package.read(prefix+"iniciar.ps1"))
                self.assertEqual(set(package.namelist()), {package_release.archive_path(name) for name in package_release.FILES})
                self.assertNotIn(b"Organizar_extracao_antiga", package.read(prefix+"README.md"))
            self.assertIn(first.name, checksum.read_text())


if __name__ == "__main__":
    unittest.main()
