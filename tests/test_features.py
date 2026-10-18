import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import app
from features import PreviewService, diagnosis, preview_command, summarize_metadata, support_report

URL = 'https://www.youtube.com/watch?v=BaW_jenozKc'
INFO = dict(id='BaW_jenozKc', title='Paganini <script>texto</script>', channel='Acervo', duration=285,
            formats=[dict(height=1080, vcodec='avc1', acodec='none', ext='mp4', url='https://private-stream'),
                     dict(height=720, vcodec='vp9', acodec='opus', ext='webm'),
                     dict(vcodec='none', acodec='aac', ext='m4a')])


class PreviewTests(unittest.TestCase):
    def test_summary_drops_stream_urls_and_preserves_available_qualities(self):
        result = summarize_metadata(INFO, URL)
        self.assertEqual(result['resolutions'], [720, 1080])
        self.assertEqual(result['source_formats'], ['M4A', 'MP4', 'WEBM'])
        self.assertTrue(result['audio_available'] and result['video_available'])
        self.assertEqual(result['duration'], 285)
        self.assertNotIn('private-stream', json.dumps(result))
        self.assertIn('<script>', result['title'])  # UI must use textContent.
        for bad in [dict(INFO, id='another'), dict(INFO, entries=[]), dict(INFO, formats={})]:
            with self.assertRaises(ValueError): summarize_metadata(bad, URL)

    def test_explicit_preview_is_readonly_cached_and_bounded(self):
        service = PreviewService()
        def run(command, **kwargs):
            self.assertEqual(command, preview_command(URL))
            self.assertIn('--skip-download', command)
            self.assertFalse(kwargs.get('shell', False))
            kwargs['stdout'].write(json.dumps(INFO).encode())
            return subprocess.CompletedProcess(command, 0)
        with patch('features.subprocess.run', side_effect=run) as process:
            self.assertFalse(service.inspect(URL)['cached'])
            self.assertTrue(service.inspect(URL)['cached'])
            self.assertEqual(process.call_count, 1)
        with patch('features.subprocess.run', side_effect=subprocess.TimeoutExpired('preview',35)):
            with self.assertRaisesRegex(ValueError,'demorou'): PreviewService().inspect(URL)
        service.lock.acquire()
        try:
            with self.assertRaisesRegex(ValueError,'andamento'): service.inspect(URL)
        finally: service.lock.release()

    def test_report_does_not_leak_job_information(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = app.Manager(Path(temp), start_worker=False)
            try:
                manager.enqueue([URL], 'mp3', True)
                manager.jobs[0].update(title='PRIVATE_TITLE', error='HTTP 429 SECRET_TOKEN C:\\PRIVATE_PATH', log='PRIVATE_LOG')
                report = support_report(manager, app.VERSION, dict(ffmpeg=True))
                self.assertIn('RATE_LIMIT', report)
                for private in [URL, 'PRIVATE_TITLE', 'SECRET_TOKEN', 'PRIVATE_PATH', 'PRIVATE_LOG', temp]:
                    self.assertNotIn(private, report)
                self.assertEqual(diagnosis('Sign in to confirm not a bot')['code'], 'SOURCE_RESTRICTION')
            finally: manager.stop()
