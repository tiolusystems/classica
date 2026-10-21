"""Module install security and independence: local fixtures, never contacting GitHub."""
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from module_manager import (
    MODULES, ModuleManager, extract_verified, release_metadata,
)


def zip_asset(product="ClassicaX", version="1.0.0"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        for item in (
            "ClassicaX.exe", "ClassicaXExtractor.exe",
            "_internal/ffmpeg.exe", "_internal/ffprobe.exe",
        ):
            package.writestr(f"{product}-{version}/{item}", b"MZ test")
    return output.getvalue()


def response_data(product="ClassicaX", repo="tiolusystems/classica-x", content=None):
    content = zip_asset(product) if content is None else content
    name = f"{product}-1.0.0-Windows-x64.zip"
    metadata = {
        "tag_name": "v1.0.0", "draft": False, "prerelease": False,
        "assets": [{
            "name": name, "size": len(content),
            "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
            "browser_download_url": f"https://github.com/{repo}/releases/download/v1.0.0/{name}",
        }]
    }
    return json.dumps(metadata).encode(), content


class Opener:
    def __init__(self, metadata, asset):
        self.metadata, self.asset = metadata, asset
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if url.startswith("https://api.github.com/repos/"):
            return io.BytesIO(self.metadata)
        if url.startswith("https://github.com/"):
            return io.BytesIO(self.asset)
        raise AssertionError("Unexpected URL: " + url)


class ModuleTests(unittest.TestCase):
    def test_release_metadata_verifies_repo_asset_and_sha(self):
        metadata, data = response_data()
        opener = Opener(metadata, data)
        actual = release_metadata("x", opener)
        self.assertEqual(actual["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(actual["size"], len(data))
        self.assertEqual(actual["version"], "1.0.0")
        self.assertEqual(len(opener.urls), 1)

    def test_wrong_origin_or_missing_digest_is_rejected(self):
        metadata, data = response_data()
        invalid = json.loads(metadata)
        invalid["assets"][0]["browser_download_url"] = "https://example.test/download.zip"
        with self.assertRaises(ValueError):
            release_metadata("x", Opener(json.dumps(invalid).encode(), data))
        invalid["assets"][0]["browser_download_url"] = "https://github.com/tiolusystems/classica-x/releases/download/v1.0.0/ClassicaX-1.0.0-Windows-x64.zip"
        invalid["assets"][0]["digest"] = ""
        with self.assertRaises(ValueError):
            release_metadata("x", Opener(json.dumps(invalid).encode(), data))

    def test_install_x_in_own_directory_not_youtube(self):
        with tempfile.TemporaryDirectory() as folder:
            metadata, data = response_data()
            root = Path(folder) / "Programs"
            manager = ModuleManager(root=root, opener=Opener(metadata, data))
            manager._install("x")
            self.assertTrue(manager.executable("x").is_file())
            self.assertTrue((root / "ClassicaX" / "current.json").is_file())
            self.assertFalse((root / "Classica" ).exists())
            self.assertFalse(manager.snapshot()["installed"]["x"]["can_rollback"])

    def test_corrupt_archive_does_not_install(self):
        with tempfile.TemporaryDirectory() as folder:
            metadata, data = response_data()
            manager = ModuleManager(root=Path(folder) / "Programs", opener=Opener(metadata, data + b"tampered"))
            with self.assertRaises(ValueError):
                manager._install("x")
            self.assertIsNone(manager.executable("x"))

    def test_archive_path_escape_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for path in ("ClassicaX-1.0.0/../../evil.txt", "ClassicaX-1.0.0/C:/evil.txt"):
                file = folder / "bad.zip"
                with zipfile.ZipFile(file, "w") as archive:
                    archive.writestr(path, b"data")
                with self.assertRaises(ValueError):
                    extract_verified(file, folder / "unpack", "ClassicaX", "1.0.0")
            file = folder / "symlink.zip"
            with zipfile.ZipFile(file, "w") as archive:
                info = zipfile.ZipInfo("ClassicaX-1.0.0/link")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, b"/bad")
            with self.assertRaises(ValueError):
                extract_verified(file, folder / "unpack2", "ClassicaX", "1.0.0")


    def test_embed_reports_idle_without_running_module(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = ModuleManager(root=Path(folder) / "Programs")
            self.assertEqual(manager.embedded_snapshot()["status"], "idle")
            self.assertIsNone(manager.embedded_snapshot()["url"])
            manager.shutdown()
            self.assertIsNone(manager.embedded_snapshot()["url"])



if __name__ == "__main__":
    unittest.main()
