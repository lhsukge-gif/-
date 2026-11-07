#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
: "${GALLERY_DATA_DIR:?Set GALLERY_DATA_DIR to the persistent storage directory}"
: "${GALLERY_SEED_DB:?Set GALLERY_SEED_DB to the transferred backup file}"
python3 deploy/prepare_data.py --source "$GALLERY_SEED_DB" --data-dir "$GALLERY_DATA_DIR"
exec python3 server.py
