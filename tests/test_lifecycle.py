"""Real application processes: reopen, exit and restart without a browser."""
import json
import shutil
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

import app


class LifecycleTests(unittest.TestCase):
    def test_probe_refuses_nonlocal_and_invalid_saved_endpoints(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for url in ['https://example.com', 'http://127.0.0.1:80@evil.test', 'http://127.0.0.1:99999', 'http://localhost:1234']:
                (root / 'instancia.json').write_text(json.dumps({'url': url}), encoding='utf-8')
                with patch('app.build_opener') as opener:
                    self.assertIsNone(app.active_instance(root))
                    opener.assert_not_called()

    def test_reopen_then_exit_and_restart_preserves_one_instance(self):
        with tempfile.TemporaryDirectory(prefix='classica lifecycle ') as temp:
            root = Path(temp)
            data = root / 'profile'
            data.mkdir()
            (data/'instancia.json').write_text('{"url":"https://example.com/stale"}', encoding='utf-8')
            command = [sys.executable, str(app.ROOT / 'app.py'), '--no-browser', '--data-dir', str(data)]
            env = dict(os.environ, PYTHONUTF8='1')
            process = None

            def start():
                return subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            def ready(child):
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    self.assertIsNone(child.poll(), 'Application exited before readiness')
                    current = app.active_instance(data)
                    if current:
                        return current
                    time.sleep(.05)
                self.fail('Application did not become ready')

            def shutdown(current):
                record = json.loads((data / 'instancia.json').read_text(encoding='utf-8'))
                request = Request(current['url']+'/api/shutdown', data=b'{}', headers={'X-Classica-Token': record['token'], 'Content-Type': 'application/json'})
                with urlopen(request, timeout=3) as response:
                    self.assertEqual(response.status, 200)

            try:
                process = start()
                current = ready(process)
                with self.assertRaises(HTTPError) as unauthorized:
                    urlopen(current['url']+'/api/instance', timeout=3)
                self.assertEqual(unauthorized.exception.code, 403)
                # Closing a tab leaves this same process alive; starting again
                # must return the existing URL and must not start another server.
                second = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=12)
                self.assertEqual(second.returncode, 0, second.stdout+second.stderr)
                self.assertIn(current['url'], second.stdout)
                # Windows venv python.exe can be a redirector: its Popen PID
                # differs from the interpreter hosting the authenticated server.
                self.assertEqual(app.active_instance(data)['pid'], current['pid'])
                self.assertIsNone(process.poll())
                # Another extracted copy/version must explain the conflict,
                # never silently route the user to the older installation.
                other = root / 'other-version'
                other.mkdir()
                for module in ('features.py', 'maintenance.py', 'module_manager.py'):
                    shutil.copyfile(app.ROOT/module, other/module)
                source = (app.ROOT/'app.py').read_text(encoding='utf-8')
                (other/'app.py').write_text(source.replace('VERSION = "2.3.0"', 'VERSION = "9.9.9"'), encoding='utf-8')
                attempt = subprocess.run([sys.executable, str(other/'app.py'), '--no-browser', '--data-dir', str(data)], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=12)
                self.assertEqual(attempt.returncode, 1)
                self.assertIn('Outra instalação', attempt.stdout)
                self.assertIn(str(app.ROOT), attempt.stdout)
                self.assertIsNone(process.poll())
                shutdown(current)
                # Restart immediately while the previous process releases locks.
                next_process = start()
                try:
                    self.assertEqual(process.wait(timeout=12), 0)
                    process = next_process
                    fresh = ready(process)
                    self.assertNotEqual(fresh['pid'], current['pid'])
                    shutdown(fresh)
                    self.assertEqual(process.wait(timeout=12), 0)
                    self.assertFalse((data/'instancia.json').exists())
                finally:
                    if next_process.poll() is None:
                        next_process.terminate()
                        next_process.wait(timeout=5)
            finally:
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
