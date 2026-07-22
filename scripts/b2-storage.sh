#!/usr/bin/env bash
#
# Manage canonical repository data mirrored to Backblaze B2.
#
# Parameters:
#   Positional command: bootstrap, reconcile, upload, download, verify, or list.
#   Optional --dry-run previews supported mutations. TRADIX_B2_ENV_FILE selects
#   the config file; TRADIX_B2_REMOTE, TRADIX_B2_BUCKET, TRADIX_B2_PREFIX, and
#   TRADIX_B2_MAX_DELETE override its settings.
# External sources:
#   Local data/artifact trees, .b2.env, the canonical manifest, and a configured
#   rclone Backblaze B2 remote.
# Side effects:
#   Depending on the command, may download or upload objects, delete remote
#   objects during sync, repair local canonical data, create directories and a
#   bootstrap marker, update the manifest, or print verification/listing output.
# Examples:
#   Bootstrap a new clone before allowing uploads:
#     scripts/b2-storage.sh bootstrap
#   Preview reconciliation without changing remote objects:
#     scripts/b2-storage.sh reconcile --dry-run
#   Verify local content and list remote objects:
#     scripts/b2-storage.sh verify
#     scripts/b2-storage.sh list

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config_file="${TRADIX_B2_ENV_FILE:-$repo_root/.b2.env}"

if [[ -f "$config_file" ]]; then
  # This file is local and ignored by Git. It should contain only assignments.
  # shellcheck disable=SC1090
  source "$config_file"
fi

remote="${TRADIX_B2_REMOTE:-b2}"
bucket="${TRADIX_B2_BUCKET:-}"
prefix="${TRADIX_B2_PREFIX:-tradix}"
max_delete="${TRADIX_B2_MAX_DELETE:-1000}"
marker_file="$repo_root/.b2-sync-initialized"
manifest_file="$repo_root/.b2-canonical-manifest.json"

usage() {
  cat <<'EOF'
Usage: scripts/b2-storage.sh <bootstrap|reconcile|upload|download|verify|list> [--dry-run]

  bootstrap Download B2 data first and mark this clone safe for uploads
  reconcile Repair canonical data, then mirror authoritative local state to B2
  upload    Alias for reconcile
  download  Copy B2 data/ and artifacts/ locally (does not delete local files)
  verify    Check that local files exist in B2 and have matching content
  list      List objects stored below the configured B2 prefix

Configuration is read from .b2.env or the TRADIX_B2_REMOTE,
TRADIX_B2_BUCKET, TRADIX_B2_PREFIX, and TRADIX_B2_MAX_DELETE environment variables.
EOF
}

command_name="${1:-}"
dry_run="${2:-}"
if [[ -z "$command_name" || ( -n "$dry_run" && "$dry_run" != "--dry-run" ) || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "error: rclone is required (version 1.59 or newer)" >&2
  exit 1
fi
if [[ -z "$bucket" ]]; then
  echo "error: set TRADIX_B2_BUCKET in .b2.env or the environment" >&2
  exit 1
fi
if [[ ! "$max_delete" =~ ^[0-9]+$ ]]; then
  echo "error: TRADIX_B2_MAX_DELETE must be a non-negative integer" >&2
  exit 1
fi

destination="${remote}:${bucket}"
if [[ -n "$prefix" ]]; then
  destination="${destination}/${prefix#/}"
  destination="${destination%/}"
fi

remote_object_count() {
  local result count
  result="$(rclone size "$destination" --fast-list --json)"
  count="$(sed -n 's/.*"count":\([0-9][0-9]*\).*/\1/p' <<<"$result")"
  if [[ -z "$count" ]]; then
    echo "error: could not determine remote object count" >&2
    return 1
  fi
  printf '%s\n' "$count"
}

require_nonempty_remote() {
  local count
  count="$(remote_object_count)"
  if [[ "$count" -eq 0 ]]; then
    echo "error: refusing to continue because $destination is empty" >&2
    return 1
  fi
}

require_initialized_clone() {
  local initialized_destination=""
  if [[ -f "$marker_file" ]]; then
    IFS= read -r initialized_destination < "$marker_file" || true
  fi
  if [[ "$initialized_destination" != "$destination" ]]; then
    echo "error: this clone is not initialized for $destination" >&2
    echo "run scripts/setup-b2-sync.sh (recommended) or scripts/b2-storage.sh bootstrap first" >&2
    return 1
  fi
}

copy_from_remote() {
  local directory
  for directory in data artifacts; do
    mkdir -p "$repo_root/$directory"
    rclone copy "$destination/$directory" "$repo_root/$directory" \
      --fast-list --transfers 16 --update "${display_args[@]}" "${extra_args[@]}"
  done
}

require_local_roots() {
  local directory
  for directory in data artifacts; do
    if [[ ! -d "$repo_root/$directory" ]]; then
      echo "error: refusing to mirror because local $directory/ is missing" >&2
      return 1
    fi
  done
}

mirror_to_remote() {
  local directory
  require_local_roots
  python3 "$repo_root/scripts/repair-canonical-data.py" repair --manifest "$manifest_file"
  for directory in data artifacts; do
    rclone sync "$repo_root/$directory" "$destination/$directory" \
      --fast-list --transfers 16 --max-delete "$max_delete" \
      "${display_args[@]}" "${extra_args[@]}"
  done
  if [[ "$dry_run" != "--dry-run" ]]; then
    python3 "$repo_root/scripts/repair-canonical-data.py" snapshot --manifest "$manifest_file"
  fi
}

extra_args=()
if [[ "$dry_run" == "--dry-run" ]]; then
  extra_args+=(--dry-run)
fi
display_args=(--stats 1m --stats-one-line)
if [[ -t 1 ]]; then
  display_args=(--progress)
fi

case "$command_name" in
  bootstrap)
    if [[ "$dry_run" == "--dry-run" ]]; then
      echo "error: --dry-run is not meaningful with bootstrap" >&2
      exit 2
    fi
    require_nonempty_remote
    copy_from_remote
    for directory in data artifacts; do
      rclone check "$destination/$directory" "$repo_root/$directory" --one-way --fast-list
    done
    python3 "$repo_root/scripts/repair-canonical-data.py" snapshot --manifest "$manifest_file"
    printf '%s\n' "$destination" > "$marker_file"
    echo "initialized clone for $destination"
    ;;
  reconcile)
    require_initialized_clone
    require_nonempty_remote
    if [[ "$dry_run" != "--dry-run" ]]; then
      exec 9>"$repo_root/.git/b2-storage.lock"
      if ! flock -n 9; then
        echo "error: another B2 reconciliation is already running" >&2
        exit 1
      fi
    fi
    mirror_to_remote
    ;;
  upload)
    require_initialized_clone
    require_nonempty_remote
    mirror_to_remote
    ;;
  download)
    require_nonempty_remote
    copy_from_remote
    ;;
  verify)
    if [[ "$dry_run" == "--dry-run" ]]; then
      echo "error: --dry-run is not meaningful with verify" >&2
      exit 2
    fi
    for directory in data artifacts; do
      rclone check "$repo_root/$directory" "$destination/$directory" --one-way --fast-list
    done
    ;;
  list)
    if [[ "$dry_run" == "--dry-run" ]]; then
      echo "error: --dry-run is not meaningful with list" >&2
      exit 2
    fi
    rclone lsf "$destination" --recursive --fast-list
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
