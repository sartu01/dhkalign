#!/usr/bin/env bash
set -euo pipefail
SRC="private/packs/public"
DST="frontend/public/data"

if [ ! -d "$SRC" ]; then
  echo "No public packs at $SRC — nothing to sync."
  exit 0
fi

mkdir -p "$DST"
rsync -a --delete "$SRC"/ "$DST"/
echo "Synced packs from $SRC -> $DST"
ls -1 "$DST"
