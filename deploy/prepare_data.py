"""Initialize persistent storage from a SQLite backup without replacing existing data."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import tempfile


def validate(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')
        works = json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])
        if not isinstance(works, list):
            raise ValueError('Invalid gallery database')
        return {'works': len(works), 'posters': sum(bool(w['poster']) for w in works),
                'comments': sum(len(w['comments']) for w in works),
                'reactions': sum(len(w['reactions']) for w in works)}


def prepare(source, directory):
    source, directory = Path(source), Path(directory)
    target = directory / 'gallery.db'
    directory.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return {'action': 'preserved', **validate(target)}
    validate(source)
    fd, temporary = tempfile.mkstemp(prefix='.gallery-', suffix='.db', dir=directory)
    os.close(fd)
    try:
        with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as src:
            with sqlite3.connect(temporary) as dst:
                src.backup(dst)
        counts = validate(Path(temporary))
        # Atomic creation; never overwrite a database created by another process.
        os.link(temporary, target)
        return {'action': 'imported', **counts}
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--data-dir', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.data_dir)))
