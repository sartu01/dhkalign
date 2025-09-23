#!/bin/bash
set -euo pipefail
SRC="README.md"
TARGETS=("docs/SECURITY.md" "docs/PROPERTY_DEFENSE.md")

for t in "${TARGETS[@]}"; do
  cp "$SRC" "$t"
  echo "✔ Synced $SRC -> $t"
done
