"""Server-only storage adapters. No Supabase credentials are sent to the browser."""
import base64
import binascii
import json
import os
from pathlib import Path
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request


class StorageError(Exception):
    pass


def decode_poster(value):
    if not value:
        return None
    try:
        header, encoded = value.split(',', 1)
        mime = header.removeprefix('data:').removesuffix(';base64')
        extensions = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}
        if header != f'data:{mime};base64' or mime not in extensions:
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > 4 * 1024 * 1024:
            raise ValueError()
        return raw, mime, extensions[mime]
    except (ValueError, binascii.Error):
        raise ValueError('4MB 이하의 PNG, JPG, WEBP, GIF 이미지를 선택해 주세요.') from None


class SQLiteStore:
    def __init__(self, directory):
        self.path = Path(directory) / 'gallery.db'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, value TEXT)')
            db.execute("INSERT OR IGNORE INTO state VALUES (1, '[]')")

    def read(self):
        with sqlite3.connect(self.path) as db:
            return json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])

    def mutate(self, callback):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute('BEGIN IMMEDIATE')
            works = json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])
            callback(works)
            db.execute('UPDATE state SET value=? WHERE id=1', (json.dumps(works, ensure_ascii=False),))

    def add(self, work):
        self.mutate(lambda works: works.insert(0, work))

    def update(self, ident, action, data):
        def change(works):
            work = next((w for w in works if w['id'] == ident), None)
            if work is None:
                raise KeyError(ident)
            if action == 'react':
                key = data['client'] + ':' + data['emoji']
                if key in work['reactions']:
                    del work['reactions'][key]
                else:
                    work['reactions'][key] = data['emoji']
            else:
                work['comments'].append(data)
        self.mutate(change)


class SupabaseStore:
    def __init__(self, url, key):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            raise ValueError('SUPABASE_URL must be the HTTPS project URL')
        if not key:
            raise ValueError('SUPABASE_SERVICE_ROLE_KEY is required')
        self.url, self.key = url.rstrip('/'), key

    def request(self, path, method='GET', data=None, headers=None, raw=False):
        h = {'apikey': self.key}
        # Legacy service_role JWTs use Authorization too; new secret keys use apikey.
        if not self.key.startswith('sb_secret_'):
            h['Authorization'] = 'Bearer ' + self.key
        if data is not None and not raw:
            data = json.dumps(data, ensure_ascii=False).encode()
            h['Content-Type'] = 'application/json'
        h.update(headers or {})
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + path, data, h, method=method), timeout=25) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            # Never expose upstream responses or credentials to users/logs.
            if exc.code == 404:
                raise KeyError('not found') from None
            raise StorageError(f'Supabase request failed (HTTP {exc.code})') from None
        except (OSError, ValueError):
            raise StorageError('Supabase connection failed') from None

    def read(self):
        rows = []
        offset = 0
        while True:
            batch = self.request(f'/rest/v1/gallery_works?select=payload&order=id.asc&limit=500&offset={offset}')
            rows.extend(w['payload'] for w in batch)
            if len(batch) < 500:
                break
            offset += len(batch)
        return sorted(rows, key=lambda w: w['created'], reverse=True)

    def add(self, work):
        payload = dict(work)
        image = decode_poster(payload.get('poster', ''))
        if image:
            raw, mime, extension = image
            filename = urllib.parse.quote(payload['id'], safe='') + '.' + extension
            self.request('/storage/v1/object/gallery-posters/' + filename, 'POST', raw,
                         {'Content-Type': mime, 'x-upsert': 'true'}, raw=True)
            payload['poster'] = self.url + '/storage/v1/object/public/gallery-posters/' + filename
        self.request('/rest/v1/gallery_works?on_conflict=id', 'POST',
                     {'id': payload['id'], 'payload': payload},
                     {'Prefer': 'resolution=ignore-duplicates,return=minimal'})

    def update(self, ident, action, data):
        result = self.request('/rest/v1/rpc/gallery_update', 'POST',
                              {'work_id': ident, 'action': action, 'input_data': data})
        if not result:
            raise KeyError(ident)


def create_store(root):
    backend = os.environ.get('GALLERY_BACKEND', 'sqlite')
    if backend == 'supabase':
        return SupabaseStore(os.environ.get('SUPABASE_URL', ''), os.environ.get('SUPABASE_SERVICE_ROLE_KEY', ''))
    if backend != 'sqlite':
        raise ValueError('Unsupported GALLERY_BACKEND')
    return SQLiteStore(os.environ.get('GALLERY_DATA_DIR', str(root / 'data')))
