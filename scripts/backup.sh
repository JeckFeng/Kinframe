#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-data/backups}"
stamp="${BACKUP_STAMP:-$(date +%Y%m%d-%H%M%S)}"
backup_dir="$BACKUP_DIR/$stamp"

if [[ -e "$backup_dir" ]]; then
  echo "Backup directory already exists: $backup_dir" >&2
  exit 1
fi

mkdir -p "$backup_dir"

scripts/backup-postgres.sh "$backup_dir"
scripts/backup-minio.sh "$backup_dir"
scripts/backup-config.sh "$backup_dir"

python3 - "$backup_dir" <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

backup_dir = Path(sys.argv[1])


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        values[key] = value
    return values


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


files = []
for path in sorted(backup_dir.rglob("*")):
    if not path.is_file() or path.name == "manifest.json":
        continue
    files.append(
        {
            "path": path.relative_to(backup_dir).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    )

postgres_counts = read_env_file(backup_dir / "postgres" / "counts.env")
minio_counts = read_env_file(backup_dir / "minio" / "counts.env")
config_metadata = read_env_file(backup_dir / "config" / "metadata.env")

manifest = {
    "kind": "kinframe-backup",
    "version": "v0.1",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "backup_dir": str(backup_dir),
    "contains_env": config_metadata.get("CONFIG_CONTAINS_ENV") == "1",
    "postgres": {
        "dump_file": postgres_counts.get("POSTGRES_DUMP_FILE"),
        "user_count": int(postgres_counts.get("POSTGRES_USER_COUNT", "0")),
        "photo_count": int(postgres_counts.get("POSTGRES_PHOTO_COUNT", "0")),
        "slide_design_count": int(postgres_counts.get("POSTGRES_SLIDE_DESIGN_COUNT", "0")),
    },
    "minio": {
        "bucket": minio_counts.get("MINIO_BUCKET"),
        "backup_dir": minio_counts.get("MINIO_BACKUP_DIR"),
        "object_count": int(minio_counts.get("MINIO_OBJECT_COUNT", "0")),
        "total_bytes": int(minio_counts.get("MINIO_TOTAL_BYTES", "0")),
    },
    "files": files,
}

(backup_dir / "manifest.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
PY

test -s "$backup_dir/manifest.json"
printf 'Backup completed: %s\n' "$backup_dir"
