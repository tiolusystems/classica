"""Explicit metadata preview and a support report that excludes personal data."""
from __future__ import annotations

import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time


def diagnosis(message: str) -> dict:
    text = str(message).lower()
    if any(x in text for x in ('429', 'too many requests', 'limite de requisi', 'limite persist')):
        code, title, action = 'RATE_LIMIT', 'O YouTube limitou as consultas.', 'Aguarde a pausa indicada e confira o vídeo no navegador antes de tentar novamente.'
    elif any(x in text for x in ('not a bot', 'sign in', 'po token', 'verificação de usuário', 'login')):
        code, title, action = 'SOURCE_RESTRICTION', 'O YouTube restringiu esta consulta.', 'Confira o vídeo no navegador. A atualização não garante remover restrições do serviço.'
    elif any(x in text for x in ('unavailable', 'private video', 'removed', 'indisponível', 'removido')):
        code, title, action = 'UNAVAILABLE', 'A gravação não está disponível nesta tentativa.', 'Confira o link e a disponibilidade da gravação no navegador.'
    elif any(x in text for x in ('timed out', 'timeout', 'connection', 'conexão', 'network')):
        code, title, action = 'NETWORK', 'Não foi possível concluir a conexão.', 'Confira a internet e tente novamente mais tarde.'
    elif any(x in text for x in ('permission', 'access denied', 'permissão', 'acesso negado')):
        code, title, action = 'FILE_ACCESS', 'Não foi possível acessar uma pasta ou arquivo.', 'Confira a pasta de destino nas Preferências e se há espaço livre.'
    elif any(x in text for x in ('format', 'formato', 'resolução')):
        code, title, action = 'FORMAT', 'A opção escolhida não pôde ser obtida.', 'Consulte os detalhes do link e experimente Melhor disponível.'
    elif any(x in text for x in ('ffmpeg', 'ffprobe', 'component', 'componente')):
        code, title, action = 'COMPONENT', 'Um componente não respondeu como esperado.', 'Encerre pelo botão Sair e abra Clássica novamente. Se persistir, copie o diagnóstico na Ajuda.'
    else:
        code, title, action = 'DOWNLOAD', 'Não foi possível concluir este download.', 'Confira o link e consulte os detalhes. O diagnóstico na Ajuda pode facilitar o suporte.'
    return {'code': code, 'summary': title, 'action': action}


def support_report(manager, version: str, dependencies: dict) -> str:
    # Whitelisted scalar information only: never serialize jobs, paths, URLs,
    # session credentials, environment variables or unfiltered process logs.
    try:
        extractor = importlib.metadata.version('yt-dlp')
    except importlib.metadata.PackageNotFoundError:
        extractor = 'ausente'
    with manager.lock:
        counts = {state: sum(j['status'] == state for j in manager.jobs)
                  for state in ('queued', 'preparing', 'downloading', 'converting', 'done', 'error', 'cancelled', 'interrupted')}
        codes = sorted({diagnosis(j.get('error', ''))['code'] for j in manager.jobs if j.get('error')})
        paused = manager.queue_pause['manual'] or time.time() < manager.queue_pause['until']
    lines = [f'Clássica {version}', f'Sistema: {platform.system()} {platform.release()} · {platform.machine()}',
             f'Python: {platform.python_version()}', f'Extrator: {extractor}',
             'Componentes: ' + ', '.join(f'{k}={"OK" if v else "ausente"}' for k, v in dependencies.items()),
             'Fila: ' + ', '.join(f'{k}={v}' for k, v in counts.items()),
             'Fila pausada: ' + ('sim' if paused else 'não'),
             'Categorias de falha: ' + (', '.join(codes) or 'nenhuma')]
    maintenance = manager.maintenance.snapshot()
    lines += ['Manutenção: ' + maintenance['phase'],
              'O relatório não inclui links, títulos, caminhos de arquivos, tokens ou dados da conta.']
    return '\n'.join(lines)


def preview_command(url: str) -> list[str]:
    return [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-playlist',
            '--skip-download', '--dump-single-json', '--no-warnings',
            '--ignore-no-formats-error', '--socket-timeout', '12', '--retries', '0',
            '--extractor-retries', '0', '--', url]


def summarize_metadata(info: dict, url: str) -> dict:
    if not isinstance(info, dict) or info.get('_type') in ('playlist', 'multi_video') or 'entries' in info:
        raise ValueError('Use o link de um único vídeo.')
    if info.get('id') != url.rsplit('=', 1)[-1]:
        raise ValueError('A origem não confirmou a gravação solicitada.')
    formats = info.get('formats', [])
    if formats is None:
        formats = []
    if not isinstance(formats, list):
        raise ValueError('A origem não informou os formatos corretamente.')
    resolutions, containers = set(), set()
    audio = video = False
    for item in formats[:5000]:
        if not isinstance(item, dict):
            continue
        has_video = item.get('vcodec') not in (None, 'none', 'images')
        audio = audio or item.get('acodec') not in (None, 'none')
        video = video or has_video
        height = item.get('height')
        if has_video and isinstance(height, (int, float)) and math.isfinite(height) and 0 < height <= 16384:
            resolutions.add(int(height))
        ext = item.get('ext')
        if ext in ('mp4', 'm4a', 'webm', 'mkv', 'ogg', 'opus'):
            containers.add(ext.upper())
    duration = info.get('duration')
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
        duration = None
    def clean(value, limit):
        return ''.join(c for c in str(value or '') if c >= ' ' and c not in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069')[:limit]
    return {'url': url, 'title': clean(info.get('title'), 300),
            'channel': clean(info.get('channel') or info.get('uploader'), 120),
            'duration': int(duration) if duration is not None else None,
            'resolutions': sorted(resolutions), 'source_formats': sorted(containers),
            'audio_available': bool(audio), 'video_available': bool(video),
            'live': info.get('is_live') is True}


class PreviewService:
    def __init__(self):
        self.lock = threading.Lock()
        self.cache = {}

    def inspect(self, url: str) -> dict:
        if not self.lock.acquire(blocking=False):
            raise ValueError('Outra consulta de detalhes está em andamento. Aguarde.')
        try:
            cached = self.cache.get(url)
            if cached and time.monotonic() - cached[0] < 600:
                return dict(cached[1], cached=True)
            # Files bound memory use even if a remote response is unexpectedly large.
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                kwargs = {'stdout': output, 'stderr': errors, 'timeout': 35}
                if os.name == 'nt':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                result = subprocess.run(preview_command(url), **kwargs)
                errors.seek(0)
                error = errors.read(16000).decode('utf-8', errors='replace')
                if result.returncode:
                    raise ValueError(error or 'A origem não respondeu à consulta.')
                if output.tell() > 8 * 1024 * 1024:
                    raise ValueError('A resposta da origem excedeu o limite da consulta.')
                output.seek(0)
                summary = summarize_metadata(json.load(output), url)
            if len(self.cache) >= 20:
                self.cache.pop(next(iter(self.cache)))
            self.cache[url] = (time.monotonic(), summary)
            return dict(summary, cached=False)
        except subprocess.TimeoutExpired:
            raise ValueError('A consulta demorou demais. Confira a conexão e tente novamente mais tarde.') from None
        except (json.JSONDecodeError, UnicodeError):
            raise ValueError('A origem não retornou os detalhes da gravação corretamente.') from None
        finally:
            self.lock.release()
