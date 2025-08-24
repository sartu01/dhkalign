#!/usr/bin/env bash
set -euo pipefail
D=private/backups/$(date +%F)_translations.db
sqlite3 backend/data/translations.db ".backup '$D'"
# Uncomment if you use GPG passphrase file:
# gpg -c --batch --passphrase-file private/.backup_pass "$D"
echo "Backup at $D"
