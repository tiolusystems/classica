"""Per-user installation and verified, non-destructive update staging.

The backend only prepares a package. The desktop controller owns the switch:
prepare dependencies -> stop old server -> open new version -> commit shortcuts.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import uuid
import zipfile

REPOSITORY = 'tiolusystems/classica'
VERSION_PATTERN = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024
PUBLIC_FILES = {'Clássica.exe', 'Leia-me.txt'}


def version_tuple(value):
    if not isinstance(value, str) or not VERSION_PATTERN.fullmatch(value):
        raise ValueError('A versão informada não é válida.')
    return tuple(int(part) for part in value.split('.'))


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or not (parsed.hostname in ('github.com', 'api.github.com') or
                                            (parsed.hostname or '').endswith('.githubusercontent.com')):
            raise ValueError('A origem do pacote não foi reconhecida. Nenhum arquivo será executado.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def official_open(url):
    return build_opener(OfficialRedirects()).open(
        Request(url, headers={'User-Agent': 'Classica', 'Accept': 'application/vnd.github+json'}), timeout=30)


def release_metadata(version=None, opener=official_open):
    if version is not None:
        version_tuple(version)
    endpoint = 'latest' if version is None else 'tags/v' + version
    with opener(f'https://api.github.com/repos/{REPOSITORY}/releases/{endpoint}') as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('A resposta da atualização excedeu o limite permitido.')
    release = json.loads(data)
    tag = release.get('tag_name', '')
    actual = tag.removeprefix('v')
    version_tuple(actual)
    if tag != 'v' + actual or release.get('draft') or release.get('prerelease') or (version and actual != version):
        raise ValueError('Não foi possível confirmar uma versão estável da Clássica.')
    name = f'Classica-{actual}-Windows-x64.zip'
    asset = next((a for a in release.get('assets', []) if a.get('name') == name), None)
    expected_url = f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
    if not asset or asset.get('browser_download_url') != expected_url:
        raise ValueError('O pacote oficial desta versão não foi encontrado.')
    digest = asset.get('digest', '')
    size = asset.get('size')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest) or not isinstance(size, int) or not 0 < size <= MAX_ARCHIVE:
        raise ValueError('O pacote não tem a verificação de integridade esperada.')
    return {'version': actual, 'url': expected_url, 'digest': digest[7:], 'size': size}


def safe_relative(value):
    if not isinstance(value, str) or '\\' in value or ':' in value or '\x00' in value:
        raise ValueError('O pacote contém um caminho inválido.')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('O pacote contém um caminho fora da pasta da aplicação.')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{i}' for p in ('COM', 'LPT') for i in range(1, 10)}
    if any(part.rstrip(' .') != part or part.split('.')[0].upper() in reserved for part in path.parts):
        raise ValueError('O pacote contém um nome incompatível com o Windows.')
    return Path(*path.parts)


def validate_layout(root: Path, version: str):
    version_tuple(version)
    exe = root / 'Clássica.exe'
    app = root / 'Componentes'
    required = ('app.py', 'web/index.html', 'requirements.lock', 'tools.lock.json', 'iniciar.ps1')
    if not exe.is_file() or exe.read_bytes()[:2] != b'MZ' or any(not (app / p).is_file() for p in required):
        raise ValueError('O pacote da aplicação está incompleto.')
    expected = f'VERSION = "{version}"'
    if expected not in (app / 'app.py').read_text(encoding='utf-8').splitlines() or \
            f'>v{version}<' not in (app / 'web/index.html').read_text(encoding='utf-8'):
        raise ValueError('O pacote mistura arquivos de versões diferentes.')


def extract_verified(archive: Path, destination: Path, version: str):
    prefix = f'Classica-{version}/'
    with zipfile.ZipFile(archive) as package:
        members = package.infolist()
        if not 1 <= len(members) <= 3000 or sum(m.file_size for m in members) > MAX_EXPANDED:
            raise ValueError('O conteúdo do pacote excedeu o limite permitido.')
        seen, validated = set(), []
        for item in members:
            # ZipInfo normalizes backslashes on Windows. Validate the original
            # name as stored, before any platform-specific normalization.
            original = item.orig_filename
            if not original.startswith(prefix):
                raise ValueError('O pacote contém arquivos fora da pasta da versão.')
            relative = original[len(prefix):].rstrip('/')
            if not relative:
                continue
            part = safe_relative(relative)
            if part.parts[0] != 'Componentes' and relative not in PUBLIC_FILES:
                raise ValueError('O pacote contém um arquivo inesperado na pasta principal.')
            mode = item.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('O pacote contém um vínculo ou tipo de arquivo não permitido.')
            key = relative.casefold()
            if key in seen:
                raise ValueError('O pacote contém nomes duplicados para o Windows.')
            seen.add(key)
            validated.append((item, part))
        for item, part in validated:
            target = destination / part
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(item) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, length=256 * 1024)
    validate_layout(destination, version)


def source_manifest(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and p.name != '.classica-package.json'}


class MaintenanceService:
    def __init__(self, program_root: Path, version: str, data_dir: Path, opener=official_open, source_files=None):
        self.root, self.version, self.data_dir = Path(program_root), version, Path(data_dir)
        local = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share')))
        self.managed_root = local / 'Programs' / 'Classica'
        self.opener, self.source_files = opener, source_files
        self.lock = threading.RLock()
        self.latest = None
        self.checked_at = 0
        self.state = {'phase': 'idle', 'message': '', 'progress': 0, 'action': None}
        self.thread = None

    def installation(self):
        try:
            record = json.loads((self.data_dir / 'instalacao.json').read_text(encoding='utf-8'))
            previous = record.get('previous')
            previous_version = previous['version'] if previous else None
            if previous_version:
                version_tuple(previous_version)
            installed = self.root.parent.resolve().is_relative_to((self.managed_root / 'versoes').resolve())
            return {'installed': installed, 'previous_version': previous_version,
                    'can_rollback': bool(previous_version and previous_version != self.version)}
        except (OSError, ValueError, TypeError, KeyError):
            return {'installed': False, 'previous_version': None, 'can_rollback': False}

    def snapshot(self):
        with self.lock:
            result = copy.deepcopy(self.state)
            result.update(self.installation())
            result['latest_version'] = self.latest['version'] if self.latest else None
            result['update_available'] = bool(self.latest and version_tuple(self.latest['version']) > version_tuple(self.version))
            result['busy'] = result['phase'] in ('downloading', 'copying', 'ready', 'preparing', 'switching')
            return result

    def check(self):
        with self.lock:
            if self.latest and time.monotonic() - self.checked_at < 30:
                return self.snapshot()
        try:
            latest = release_metadata(opener=self.opener)
        except (OSError, ValueError, KeyError, TypeError):
            raise ValueError('Não foi possível consultar as versões oficiais no GitHub. Confira a conexão e tente novamente mais tarde.') from None
        with self.lock:
            self.latest, self.checked_at = latest, time.monotonic()
        return self.snapshot()

    def _set(self, **values):
        with self.lock:
            self.state.update(values)

    def begin(self, kind):
        if kind not in ('install', 'update', 'rollback'):
            raise ValueError('Operação de manutenção inválida.')
        with self.lock:
            if self.snapshot()['busy']:
                raise ValueError('Outra preparação está em andamento.')
            if kind == 'install' and self.installation()['installed']:
                raise ValueError('Esta versão já está instalada no perfil do usuário.')
            if kind == 'rollback' and not self.installation()['can_rollback']:
                raise ValueError('Não há uma versão anterior disponível para restaurar.')
            action_id = uuid.uuid4().hex
            self.state = {'phase': 'copying' if kind == 'install' else 'downloading',
                          'message': 'Preparando a versão. A aplicação atual continua aberta.',
                          'progress': 0, 'action': None}
            self.thread = threading.Thread(target=self._prepare, args=(kind, action_id), daemon=True)
            self.thread.start()
        return self.snapshot()

    def _prepare(self, kind, action_id):
        staging = None
        try:
            self.managed_root.mkdir(parents=True, exist_ok=True)
            staging = self.managed_root / ('.preparacao-' + action_id)
            staging.mkdir()
            content = staging / 'package'
            content.mkdir()
            if kind == 'install':
                from scripts.package_release import FILES, USER_FILES
                for name in self.source_files or FILES:
                    relative = safe_relative(name)
                    source = self.root.parent / relative if name in USER_FILES else self.root / relative
                    target = content / relative if name in USER_FILES else content / 'Componentes' / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                version, digest = self.version, None
                validate_layout(content, version)
            else:
                if kind == 'rollback':
                    desired = self.installation()['previous_version']
                    metadata = release_metadata(desired, self.opener)
                else:
                    self.check()
                    metadata = dict(self.latest)
                    if version_tuple(metadata['version']) <= version_tuple(self.version):
                        raise ValueError('Você já está usando a versão mais recente disponível.')
                version, digest = metadata['version'], metadata['digest']
                archive = staging / 'package.zip'
                hasher, total = hashlib.sha256(), 0
                with self.opener(metadata['url']) as response, archive.open('xb') as output:
                    while chunk := response.read(256 * 1024):
                        total += len(chunk)
                        if total > MAX_ARCHIVE or total > metadata['size']:
                            raise ValueError('O download excedeu o tamanho esperado.')
                        hasher.update(chunk)
                        output.write(chunk)
                        self._set(progress=min(99, int(total * 100 / metadata['size'])))
                if total != metadata['size'] or hasher.hexdigest() != digest:
                    raise ValueError('A verificação SHA256 falhou. O pacote não será executado.')
                extract_verified(archive, content, version)
            files = source_manifest(content)
            target = self.managed_root / 'versoes' / ('Classica-' + version)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                # Never replace an existing version, runtime or user file.
                for name, expected in files.items():
                    existing = target / safe_relative(name)
                    if not existing.resolve().is_relative_to(target.resolve()) or not existing.is_file() or hashlib.sha256(existing.read_bytes()).hexdigest() != expected:
                        raise ValueError('Já existe uma pasta desta versão com arquivos diferentes. Nenhum arquivo foi substituído.')
            else:
                atomic_json(content / '.classica-package.json', {'version': version, 'digest': digest, 'files': files})
                content.replace(target)
            action = {'id': action_id, 'kind': kind, 'target': str(target.resolve()), 'version': version}
            self._set(phase='ready', message='Pacote verificado. Preparando a abertura da versão.', progress=100, action=action)
        except Exception as error:
            message = str(error) if isinstance(error, ValueError) else 'Não foi possível preparar a versão. Confira a conexão, o espaço livre e tente novamente.'
            self._set(phase='error', message=message[:500], action=None)
        finally:
            if staging:
                shutil.rmtree(staging, ignore_errors=True)

    def desktop_action(self):
        with self.lock:
            return copy.deepcopy(self.state['action']) if self.state['phase'] in ('ready', 'preparing') else None

    def preparing(self, action_id):
        with self.lock:
            if self.state['phase'] != 'ready' or not self.state['action'] or self.state['action']['id'] != action_id:
                raise ValueError('Preparação não reconhecida.')
            self._set(phase='preparing', message='Preparando componentes. A versão atual será mantida se houver uma falha.')

    def switching(self, action_id):
        with self.lock:
            if self.state['phase'] != 'preparing' or self.state['action']['id'] != action_id:
                raise ValueError('A nova versão ainda não está pronta para abrir.')
            self._set(phase='switching', message='Abrindo a versão preparada. Você pode fechar esta aba quando a nova janela aparecer.')

    def failed(self, action_id):
        with self.lock:
            if self.state['action'] and self.state['action']['id'] == action_id:
                self._set(phase='error', message='A manutenção não foi concluída. A versão anterior foi preservada.', action=None)
