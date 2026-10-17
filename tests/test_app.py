import http.client
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

URL = "https://www.youtube.com/watch?v=BaW_jenozKc"


class IsolatedApp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manager = app.Manager(self.root / "data", start_worker=False)
        self.manager.set_folder(str(self.root / "music"))

    def tearDown(self):
        self.manager.stop()
        self.temp.cleanup()

    def add(self, **kwargs):
        return self.manager.enqueue(kwargs.get("urls", [URL]), kwargs.get("format_", "mp3"), kwargs.get("authorized", True))


class AppTests(IsolatedApp):
    def test_friendly_error_explains_youtube_rate_limit_recovery(self):
        log = "HTTP Error 429: Too Many Requests\nERROR: Sign in to confirm you're not a bot\nMissing required Visitor Data"
        message = app.friendly_error(log)
        self.assertIn("limitou as requisições", message)
        self.assertIn("Atualizar.bat", message)
        self.assertIn("não contorna CAPTCHA", message)
        self.assertIn("não garante", message)

    def test_format_unavailable_is_not_misreported_as_removed_video(self):
        self.assertIn("formato ou a resolução", app.friendly_error("ERROR: Requested format is not available"))
        self.assertIn("PO Token", app.friendly_error("Missing required Visitor Data"))
        self.assertFalse(app.rate_limited("video 14293456789 title"))

    def test_rate_limit_retries_once_then_requires_manual_resume(self):
        self.add()
        job = self.manager.jobs[0]
        with patch.object(app.time, "time", return_value=1000):
            job["log"] = "WARNING: HTTP Error 429: Too Many Requests\nERROR: Sign in to confirm you are not a bot"
            self.manager.record_failure(job)
            self.assertEqual(job["status"], "queued")
            self.assertEqual(job["auto_retry_count"], 1)
            self.assertEqual(self.manager.queue_pause["until"], 1060)
            with self.assertRaises(ValueError):
                self.manager.resume()
            self.manager.record_failure(job)
            self.assertEqual(job["status"], "error")
            self.assertTrue(self.manager.queue_pause["manual"])
            self.manager.save()
            restored = app.Manager(self.root / "data", start_worker=False)
            self.assertTrue(restored.queue_pause["manual"])
            restored.stop()
            with self.assertRaises(ValueError):
                self.manager.retry(job["id"])
        with patch.object(app.time, "time", return_value=1061):
            self.manager.retry(job["id"])
            self.assertFalse(self.manager.queue_pause["manual"])
            self.assertEqual(job["auto_retry_count"], 0)

    def test_paused_worker_does_not_start_queued_downloads(self):
        self.add()
        self.manager.queue_pause = {"until": time.time() + 60, "manual": False, "reason": "HTTP 429"}
        with patch.object(app.subprocess, "Popen") as launch:
            self.manager.worker = threading.Thread(target=self.manager.run, daemon=True)
            self.manager.worker.start()
            self.manager.wake.set()
            time.sleep(.15)
            self.manager.stop()
            launch.assert_not_called()

    @unittest.skipUnless(shutil.which("ffprobe"), "FFprobe ausente")
    def test_html_response_cannot_pass_media_validation(self):
        self.add()
        job = self.manager.jobs[0]
        file = Path(job["folder"]) / "false-audio.webm"
        file.write_text("<html><h1>Site Unavailable</h1></html>")
        job["file"] = str(file)
        with self.assertRaisesRegex(ValueError, "não contém"):
            app.verify_media(job)
        self.assertTrue(file.is_file(), "Invalid output must be preserved for inspection")

    def test_edge_session_is_explicit_fixed_and_never_exports_cookies(self):
        self.add()
        self.assertNotIn("--cookies-from-browser", app.command_for(self.manager.jobs[0]))
        self.manager.enqueue([URL], "m4a", True, use_edge_session=True)
        command = app.command_for(self.manager.jobs[-1])
        self.assertEqual(command[command.index("--cookies-from-browser") + 1], "edge:Default")
        self.assertIn("--no-cache-dir", command)
        self.assertNotIn("--cookies", command)
        self.assertNotIn("use_edge_session", self.manager.state_file.read_text())
        restored = app.Manager(self.root / "data", start_worker=False)
        self.assertFalse(restored.jobs[-1]["use_edge_session"])
        restored.stop()
        for value in ["edge", "true", 1, None, {"profile": "secret"}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.manager.enqueue([URL], "mp3", True, use_edge_session=value)

    def test_retry_uses_current_consent_not_previous_job_consent(self):
        self.manager.enqueue([URL], "mp3", True, use_edge_session=True)
        job = self.manager.jobs[0]
        self.manager.cancel(job["id"])
        self.manager.retry(job["id"])
        self.assertFalse(job["use_edge_session"])
        self.manager.cancel(job["id"])
        self.manager.retry(job["id"], use_edge_session=True)
        self.assertTrue(job["use_edge_session"])
        self.manager.cancel(job["id"])
        with self.assertRaises(ValueError):
            self.manager.retry(job["id"], use_edge_session="edge")

    def test_edge_cookie_errors_have_safe_guidance_before_permission_fallback(self):
        for log in ["ERROR: Could not copy Chrome cookie database: Permission denied", "ERROR: Failed to decrypt with DPAPI", "ERROR: could not find Edge cookies database"]:
            with self.subTest(log=log):
                message = app.friendly_error(log)
                self.assertIn("sessão do Edge", message)
                self.assertIn("Não desative proteções", message)
                self.assertNotIn("espaço livre", message)

    def test_video_resolution_queue_and_file_names_are_distinct(self):
        first = self.manager.enqueue([URL], "mp4", True, "720")
        second = self.manager.enqueue([URL], "mp4", True, "1080")
        duplicate = self.manager.enqueue([URL], "mp4", True, "720")
        self.assertEqual((first["added"], second["added"], duplicate["skipped"]), (1, 1, 1))
        names = [app.command_for(j)[app.command_for(j).index("-o")+1] for j in self.manager.jobs]
        self.assertNotEqual(names[0], names[1])
        for invalid in ["99999", "720;calc", None, 720]:
            with self.assertRaises(ValueError):
                self.manager.enqueue([URL], "mp4", True, invalid)

    def test_normalizes_supported_links_and_strips_playlist(self):
        urls = [URL + "&list=PL123&index=8", "https://youtu.be/BaW_jenozKc?t=23",
                "https://m.youtube.com/watch?v=BaW_jenozKc",
                "https://music.youtube.com/watch?v=BaW_jenozKc",
                "https://youtube.com/shorts/BaW_jenozKc",
                "https://www.youtube.com/live/BaW_jenozKc"]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(app.canonical_url(url), URL)

    def test_rejects_remote_domains_playlist_and_shell_inputs(self):
        for url in ["file:///etc/passwd", "https://youtube.com.attacker.org/watch?v=BaW_jenozKc",
                    "https://www.youtube.com/playlist?list=PLxyz", "ytsearch:Beethoven",
                    "https://user:pass@youtube.com/watch?v=BaW_jenozKc",
                    "https://youtube.com:8080/watch?v=BaW_jenozKc", "$(calc.exe)",
                    "https://youtu.be/invalid", None, "https://youtu.be/BaW_jenozKc/extra"]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    app.canonical_url(url)

    def test_authorization_and_format_required(self):
        for kwargs in [{"authorized": False}, {"authorized": "true"}, {"format_": "exe"}]:
            with self.assertRaises(ValueError):
                self.add(**kwargs)
        self.assertEqual(self.manager.jobs, [])

    def test_invalid_batch_is_atomic(self):
        with self.assertRaises(ValueError):
            self.add(urls=[URL, "https://attacker.org"])
        self.assertEqual(self.manager.jobs, [])

    def test_queue_limits_and_duplicates(self):
        self.assertEqual(self.add(urls=[URL, URL])["added"], 1)
        self.assertEqual(self.add()["skipped"], 1)
        self.assertEqual(self.add(format_="original")["added"], 1)
        with self.assertRaises(ValueError):
            self.add(urls=[URL] * 51)

    def test_history_recovery_requires_explicit_retry(self):
        self.add()
        restored = app.Manager(self.root / "data", start_worker=False)
        self.assertEqual(restored.jobs[0]["status"], "interrupted")
        self.assertEqual(restored.folder, self.manager.folder)
        restored.retry(restored.jobs[0]["id"])
        self.assertEqual(restored.jobs[0]["status"], "queued")
        restored.stop()

    def test_cancel_and_clear_preserve_files(self):
        self.add()
        job = self.manager.jobs[0]
        audio = Path(job["folder"]) / "saved.mp3"
        audio.write_bytes(b"test")
        self.manager.cancel(job["id"])
        self.assertEqual(job["status"], "cancelled")
        self.manager.clear()
        self.assertEqual(self.manager.jobs, [])
        self.assertTrue(audio.exists())

    def test_progress_parser_and_file_boundary(self):
        self.add()
        job = self.manager.jobs[0]
        self.manager.parse_line(job, 'CLASSICA_TITLE:Bach — "Cantata" <script>')
        self.assertIn("Cantata", job["title"])
        progress = dict(status="downloading", downloaded_bytes=50, total_bytes=100, speed=1024*1024, eta=3)
        self.manager.parse_line(job, "CLASSICA_PROGRESS:" + json.dumps(progress))
        self.assertEqual(job["progress"], 50)
        self.assertEqual(job["speed"], "1.0 MB/s")
        outside = self.root / "secret.mp3"
        outside.write_bytes(b"secret")
        self.manager.parse_line(job, "CLASSICA_FILE:" + str(outside))
        self.assertEqual(job["file"], "")
        inside = Path(job["folder"]) / "Bach.mp3"
        inside.write_bytes(b"audio")
        self.manager.parse_line(job, "CLASSICA_FILE:" + str(inside))
        self.assertEqual(job["file"], str(inside))

    def test_command_is_audio_only_and_configuration_isolated(self):
        for format_ in app.FORMATS:
            self.add(format_=format_)
            command = app.command_for(self.manager.jobs[-1])
            self.assertIn("--ignore-config", command)
            self.assertIn("--no-playlist", command)
            self.assertIn("--windows-filenames", command)
            self.assertNotIn("--no-check-certificates", command)
            self.assertEqual(command[-2:], ["--", URL])
            if format_ == "original":
                self.assertNotIn("--audio-format", command)
            else:
                self.assertIn("-x", command)
                self.assertEqual(command[command.index("--audio-format")+1], "vorbis" if format_ == "ogg" else format_)

    def test_worker_completes_and_verifies_output_file(self):
        def fake_command(job):
            file = str(Path(job["folder"]) / "fixture.mp3")
            code = "from pathlib import Path; import json,wave; p=Path("+repr(file)+"); w=wave.open(str(p),'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\\0'*16000); w.close(); print('CLASSICA_TITLE:Fixture'); print('CLASSICA_PROGRESS:'+json.dumps(dict(status='finished',downloaded_bytes=16000,total_bytes=16000))); print('CLASSICA_FILE:'+str(p))"
            return [sys.executable, "-c", code]
        self.add()
        with patch.object(app, "dependencies", return_value=dict(yt_dlp=True, ffmpeg=True, ffprobe=True, deno=True)), patch.object(app, "command_for", side_effect=fake_command):
            self.manager.worker = threading.Thread(target=self.manager.run, daemon=True)
            self.manager.worker.start()
            deadline = time.monotonic()+5
            while self.manager.jobs[0]["status"] not in app.TERMINAL and time.monotonic()<deadline:
                time.sleep(.03)
            self.assertEqual(self.manager.jobs[0]["status"], "done")
            self.assertEqual(self.manager.jobs[0]["progress"], 100)
            self.manager.stop()

    def test_worker_never_marks_missing_file_success(self):
        self.add()
        with patch.object(app, "dependencies", return_value=dict(yt_dlp=True, ffmpeg=True, ffprobe=True, deno=True)), patch.object(app, "command_for", return_value=[sys.executable, "-c", "print('CLASSICA_TITLE:No file')"]):
            self.manager.worker = threading.Thread(target=self.manager.run, daemon=True)
            self.manager.worker.start()
            deadline = time.monotonic()+5
            while self.manager.jobs[0]["status"] not in app.TERMINAL and time.monotonic()<deadline:
                time.sleep(.03)
            self.assertEqual(self.manager.jobs[0]["status"], "error")
            self.manager.stop()

    def test_worker_rejects_success_exit_with_invalid_media(self):
        self.add()
        file = str(Path(self.manager.folder) / "error.webm")
        code = "from pathlib import Path; p=Path("+repr(file)+"); p.write_text('<html>Site Unavailable</html>'); print('CLASSICA_FILE:'+str(p))"
        with patch.object(app, "dependencies", return_value=dict(yt_dlp=True, ffmpeg=True, ffprobe=True, deno=True)), patch.object(app, "command_for", return_value=[sys.executable, "-c", code]):
            self.manager.worker = threading.Thread(target=self.manager.run, daemon=True)
            self.manager.worker.start()
            deadline = time.monotonic()+5
            while self.manager.jobs[0]["status"] not in app.TERMINAL and time.monotonic()<deadline:
                time.sleep(.03)
            self.assertEqual(self.manager.jobs[0]["status"], "error")
            self.assertNotEqual(self.manager.jobs[0]["progress"], 100)
            self.manager.stop()

    def test_cancels_running_process(self):
        self.add()
        with patch.object(app, "dependencies", return_value=dict(yt_dlp=True, ffmpeg=True, ffprobe=True, deno=True)), patch.object(app, "command_for", return_value=[sys.executable, "-u", "-c", "import time; print('CLASSICA_TITLE:Long fixture'); time.sleep(30)"]):
            self.manager.worker = threading.Thread(target=self.manager.run, daemon=True)
            self.manager.worker.start()
            deadline = time.monotonic()+5
            while not self.manager.process and time.monotonic()<deadline:
                time.sleep(.03)
            self.assertIsNotNone(self.manager.process)
            process = self.manager.process
            self.manager.cancel(self.manager.jobs[0]["id"])
            process.wait(timeout=3)
            self.assertEqual(self.manager.jobs[0]["status"], "cancelled")
            self.manager.stop()


class HttpTests(IsolatedApp):
    # HTTP tests reuse the isolated temporary application but not base tests.
    def setUp(self):
        super().setUp()
        self.server = app.create_server(self.manager)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    def request(self, path, data=None, token=True, headers=None):
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        hdr = {"Content-Type": "application/json"}
        if token:
            hdr["X-Classica-Token"] = self.server.token
        hdr.update(headers or {})
        client.request("POST" if data is not None else "GET", path, body=json.dumps(data) if data is not None else None, headers=hdr)
        response = client.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        client.close()
        return result

    def test_api_access_and_cross_origin_rejection(self):
        self.assertEqual(self.request("/api/state", token=False)[0], 403)
        self.assertEqual(self.request("/api/state")[0], 200)
        self.assertEqual(self.request("/api/clear", {}, headers={"Origin":"https://attacker.org"})[0], 403)
        self.assertEqual(self.request("/api/clear", {}, token=False)[0], 403)
        self.assertEqual(self.request("/", headers={"Host":"attacker.org"})[0], 403)

    def test_html_token_and_static_files(self):
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(self.server.token.encode(), body)
        self.assertNotIn(b"__TOKEN__", body)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(self.request("/app.js")[0], 200)
        self.assertEqual(self.request("/style.css")[0], 200)
        self.assertEqual(self.request("/../app.py")[0], 404)

    def test_api_enqueue_validation(self):
        self.assertEqual(self.request("/api/enqueue", {"urls":[URL],"format":"mp3","authorized":False})[0], 400)
        status, _, body = self.request("/api/enqueue", {"urls":[URL],"format":"mp3","authorized":True})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["added"], 1)
        self.assertEqual(self.request("/api/enqueue", {"urls":[URL],"format":"mp4","authorized":True,"resolution":"720"})[0], 200)
        self.assertEqual(self.manager.jobs[-1]["resolution"], "720")
        self.assertEqual(self.request("/api/enqueue", {"urls":[URL],"format":"mp4","authorized":True,"resolution":"garbage"})[0], 400)

    def test_api_edge_consent_and_retry_validation(self):
        payload = {"urls": [URL], "format": "mp3", "authorized": True, "use_edge_session": "edge:arbitrary"}
        self.assertEqual(self.request("/api/enqueue", payload)[0], 400)
        payload["use_edge_session"] = True
        self.assertEqual(self.request("/api/enqueue", payload)[0], 200)
        job = self.manager.jobs[0]
        self.assertTrue(job["use_edge_session"])
        self.manager.cancel(job["id"])
        self.assertEqual(self.request("/api/retry", {"id":job["id"], "use_edge_session": "true"})[0], 400)
        self.assertEqual(self.request("/api/retry", {"id":job["id"]})[0], 200)
        self.assertFalse(job["use_edge_session"])

    def test_file_delivery_and_escape_denied(self):
        self.add()
        job = self.manager.jobs[0]
        file = Path(job["folder"]) / "Bach - São João.mp3"
        file.write_bytes(b"fixture_audio")
        job.update(status="done", file=str(file))
        status, headers, body = self.request("/file/" + job["id"])
        self.assertEqual(status, 200)
        self.assertEqual(body, b"fixture_audio")
        self.assertIn("filename*=UTF-8''", headers["Content-Disposition"])
        outside = self.root / "outside.mp3"
        outside.write_bytes(b"secret")
        job["file"] = str(outside)
        self.assertEqual(self.request("/file/" + job["id"])[0], 404)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg ausente")
class AudioConversionTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("yt_dlp"), "yt-dlp ausente")
    def test_real_video_download_keeps_picture_and_sound_in_each_container(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "fixture.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=160x90:r=10:d=1", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(source)], check=True, capture_output=True)
            for format_ in app.VIDEO_FORMATS:
                with self.subTest(format=format_):
                    folder = root / format_
                    folder.mkdir()
                    job = dict(url=source.as_uri(), folder=str(folder), format=format_, resolution="best", file="", title="", log="", progress=0)
                    cmd = app.command_for(job)
                    self.assertNotIn("-x", cmd)
                    cmd.insert(cmd.index("--"), "--enable-file-urls")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                    manager = app.Manager(root / ("data-" + format_), start_worker=False)
                    for line in result.stdout.splitlines():
                        manager.parse_line(job, line)
                    self.assertTrue(Path(job["file"]).is_file())
                    self.assertEqual(Path(job["file"]).suffix, "." + format_)
                    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", job["file"]], check=True, capture_output=True, text=True)
                    streams = json.loads(probe.stdout)["streams"]
                    self.assertEqual({s["codec_type"] for s in streams}, {"video", "audio"})
                    self.assertEqual(next(s for s in streams if s["codec_type"] == "video")["height"], 90)

    @unittest.skipUnless(importlib.util.find_spec("yt_dlp"), "yt-dlp ausente")
    def test_video_selector_caps_resolution_and_merges_audio(self):
        import yt_dlp
        formats = [dict(format_id="a", url="https://example.com/a", vcodec="none", acodec="aac", ext="m4a")]
        for height in [360, 720, 1080, 1440, 2160]:
            formats.append(dict(format_id=str(height), url="https://example.com/v", vcodec="h264", acodec="none", height=height, width=height*16//9, ext="mp4"))
        with yt_dlp.YoutubeDL({"quiet":True}) as ydl:
            for resolution, expected in [("480",360),("720",720),("1080",1080),("1440",1440),("2160",2160),("best",2160)]:
                selected = list(ydl.build_format_selector(app.video_selector(resolution))({"formats":formats,"incomplete_formats":False,"has_merged_format":False}))
                self.assertEqual(len(selected),1)
                self.assertEqual(selected[0]["requested_formats"][0]["height"], expected)
                self.assertEqual(selected[0]["requested_formats"][1]["acodec"], "aac")

    def test_real_ffmpeg_converts_synthetic_audio_to_mp3_and_m4a(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "sintetico.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(source)], check=True, capture_output=True)
            for ext, codec, expected in [("mp3", "libmp3lame", "mp3"), ("m4a", "aac", "aac")]:
                output = root / ("teste." + ext)
                subprocess.run(["ffmpeg", "-v", "error", "-i", str(source), "-c:a", codec, "-b:a", "320k", str(output)], check=True, capture_output=True)
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)], check=True, capture_output=True, text=True)
                self.assertEqual(json.loads(probe.stdout)["streams"][0]["codec_name"], expected)
                self.assertGreater(output.stat().st_size, 1000)

    @unittest.skipUnless(importlib.util.find_spec("yt_dlp"), "yt-dlp ausente")
    def test_real_extractor_to_final_file_in_all_formats(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "fixture.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(source)], check=True, capture_output=True)
            for format_ in app.FORMATS:
                with self.subTest(format=format_):
                    folder = root / format_
                    folder.mkdir()
                    job = dict(url=source.as_uri(), folder=str(folder), format=format_, file="", title="", log="", progress=0)
                    cmd = app.command_for(job)
                    # Enable the file protocol only in this test; never in the application.
                    cmd.insert(cmd.index("--"), "--enable-file-urls")
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
                    manager = app.Manager(root / ("data-" + format_), start_worker=False)
                    for line in result.stdout.splitlines():
                        manager.parse_line(job, line)
                    self.assertTrue(Path(job["file"]).is_file())
                    self.assertEqual(Path(job["file"]).suffix, ".wav" if format_ == "original" else "." + format_)
                    self.assertEqual(job["title"], "fixture")


if __name__ == "__main__":
    unittest.main()
