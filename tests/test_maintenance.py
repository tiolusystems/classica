import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

import app
import maintenance as mt

VERSION = app.VERSION


def package(version=VERSION, extra=None):
    files = {'Clássica.exe': b'MZ-native', 'Leia-me.txt': b'guide',
             'Componentes/app.py': f'VERSION = "{version}"\n'.encode(),
             'Componentes/web/index.html': f'<span>v{version}</span>'.encode(),
             'Componentes/requirements.lock': b'locked', 'Componentes/tools.lock.json': b'{}',
             'Componentes/iniciar.ps1': b'# setup'}
    files.update(extra or {})
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        for name, value in files.items():
            original = f'Classica-{version}/'+name
            info = zipfile.ZipInfo(original)
            info.filename = info.orig_filename = original
            z.writestr(info, value)
    return output.getvalue()


def metadata(raw, version=VERSION):
    name = f'Classica-{version}-Windows-x64.zip'
    return dict(tag_name='v'+version, draft=False, prerelease=False, assets=[dict(name=name,
                size=len(raw), digest='sha256:'+hashlib.sha256(raw).hexdigest(),
                browser_download_url=f'https://github.com/tiolusystems/classica/releases/download/v{version}/{name}')])


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, LOCALAPPDATA=str(self.root/'profile'))
        self.environment.start()

    def tearDown(self):
        self.environment.stop(); self.temp.cleanup()

    def test_metadata_requires_official_asset_and_digest(self):
        raw = package()
        good = metadata(raw)
        self.assertEqual(mt.release_metadata(opener=lambda u: io.BytesIO(json.dumps(good).encode()))['version'], VERSION)
        for bad in [dict(good, prerelease=True), dict(good, tag_name='v1.2'),
                    dict(good, assets=[dict(good['assets'][0], browser_download_url='https://evil.test/a.zip')]),
                    dict(good, assets=[dict(good['assets'][0], digest=None)])]:
            with self.assertRaises((ValueError,TypeError)):
                mt.release_metadata(opener=lambda u: io.BytesIO(json.dumps(bad).encode()))

    def test_zip_rejects_traversal_windows_devices_extra_root_and_links(self):
        for path in ['../escape', 'Componentes/../../escape', 'Componentes/C:evil',
                     'Componentes/CON.txt', 'Componentes/trailing.', 'extra.exe', 'Componentes/a\\b']:
            file = self.root/'test.zip'; file.write_bytes(package(extra={path:b'bad'}))
            with self.assertRaises(ValueError): mt.extract_verified(file, self.root/'unused', VERSION)
        raw = io.BytesIO(package())
        with zipfile.ZipFile(raw,'a') as z:
            link = zipfile.ZipInfo(f'Classica-{VERSION}/Componentes/link')
            link.create_system=3; link.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(link,b'../../outside')
        file = self.root/'link.zip'; file.write_bytes(raw.getvalue())
        with self.assertRaises(ValueError): mt.extract_verified(file,self.root/'unused',VERSION)
        self.assertFalse((self.root/'escape').exists())

    def service(self, raw=None, release=None):
        raw = raw if raw is not None else package()
        release = release or metadata(raw)
        def open_(url): return io.BytesIO(json.dumps(release).encode() if 'api.github.com' in url else raw)
        return mt.MaintenanceService(self.root/'portable'/'Componentes', '2.1.2', self.root/'data', opener=open_)

    def finish(self, service, kind='update'):
        service.begin(kind); service.thread.join(5)
        self.assertFalse(service.thread.is_alive())
        return service.snapshot()

    def test_verified_update_preserves_history_and_switch_requires_matching_action(self):
        service = self.service()
        service.data_dir.mkdir(); history=service.data_dir/'historico.json'; history.write_text('private history')
        state = self.finish(service)
        self.assertEqual(state['phase'],'ready')
        self.assertEqual(history.read_text(),'private history')
        target=Path(state['action']['target'])
        self.assertTrue((target/'.classica-package.json').is_file())
        with self.assertRaises(ValueError): service.switching(state['action']['id'])
        with self.assertRaises(ValueError): service.preparing('f'*32)
        service.preparing(state['action']['id'])
        self.assertEqual(service.desktop_action()['target'],str(target))
        service.switching(state['action']['id'])
        self.assertEqual(service.snapshot()['phase'],'switching')
        service.failed(state['action']['id'])
        self.assertFalse(service.snapshot()['busy'])

    def test_corrupt_download_or_existing_modified_version_is_never_executed(self):
        good=package(); release=metadata(good)
        state=self.finish(self.service(raw=good+b'corrupt',release=release))
        self.assertEqual(state['phase'],'error'); self.assertIsNone(state['action'])
        service=self.service(); state=self.finish(service)
        target=Path(state['action']['target']); protected=target/'Componentes/app.py'; protected.write_text('modified')
        service.failed(state['action']['id'])
        state=self.finish(service)
        self.assertEqual(state['phase'],'error'); self.assertEqual(protected.read_text(),'modified')

    def test_install_copies_only_distribution_files_and_keeps_original(self):
        src=self.root/'portable'; src.mkdir()
        archive=self.root/'test.zip'; archive.write_bytes(package())
        mt.extract_verified(archive,src,VERSION)
        (src/'Componentes/private.txt').write_text('private')
        files=['Clássica.exe','Leia-me.txt','app.py','web/index.html','requirements.lock','tools.lock.json','iniciar.ps1']
        service=mt.MaintenanceService(src/'Componentes', VERSION,self.root/'data',source_files=files)
        state=self.finish(service,'install'); self.assertEqual(state['phase'],'ready')
        target=Path(state['action']['target'])
        self.assertFalse((target/'Componentes/private.txt').exists())
        self.assertTrue((src/'Componentes/private.txt').exists())

    def test_manager_blocks_mutations_during_maintenance_and_requires_desktop(self):
        manager=app.Manager(self.root/'data',start_worker=False)
        try:
            with self.assertRaisesRegex(ValueError,'ícone'): manager.begin_maintenance('install')
            manager.desktop_seen=time.monotonic()
            manager.maintenance._set(phase='preparing')
            with self.assertRaises(ValueError): manager.enqueue(['https://www.youtube.com/watch?v=BaW_jenozKc'],'mp3',True)
            with self.assertRaises(ValueError): manager.resume()
        finally: manager.stop()

    def test_rollback_downloads_official_previous_version(self):
        service=self.service(); service.data_dir.mkdir()
        mt.atomic_json(service.data_dir/'instalacao.json', {'previous':{'version':VERSION}})
        state=self.finish(service,'rollback')
        self.assertEqual(state['phase'],'ready'); self.assertEqual(state['action']['version'],VERSION)
