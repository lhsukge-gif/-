"""One-time, repeatable migration; retains source DB and skips existing work IDs."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import SupabaseStore


def migrate(source, store):
    with sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Source database integrity check failed')
        works = json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])
    existing = {w['id'] for w in store.read()}
    count = 0
    for work in works:
        if work['id'] not in existing:
            store.add(work)
            count += 1
    remote = {w['id']: w for w in store.read()}
    for work in works:
        if work['id'] not in remote:
            raise RuntimeError('Migration verification failed')
        if work['id'] not in existing:
            saved = remote[work['id']]
            assert saved['comments'] == work['comments'] and saved['reactions'] == work['reactions']
            assert bool(saved['poster']) == bool(work['poster'])
    return {'imported': count, 'skipped': len(works) - count, 'total': len(remote)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    store = SupabaseStore(os.environ.get('SUPABASE_URL', ''), os.environ.get('SUPABASE_SERVICE_ROLE_KEY', ''))
    print(json.dumps(migrate(args.source, store)))
