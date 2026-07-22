#!/usr/bin/env bash
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

usage() {
  cat <<'EOF'
Usage: scripts/b2-storage.sh <upload|download|verify|list> [--dry-run]

  upload    Copy local data/ and artifacts/ to B2 (does not delete remote files)
  download  Copy B2 data/ and artifacts/ locally (does not delete local files)
  verify    Check that local files exist in B2 and have matching content
  list      List objects stored below the configured B2 prefix

Configuration is read from .b2.env or the TRADIX_B2_REMOTE,
TRADIX_B2_BUCKET, and TRADIX_B2_PREFIX environment variables.
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

destination="${remote}:${bucket}"
if [[ -n "$prefix" ]]; then
  destination="${destination}/${prefix#/}"
  destination="${destination%/}"
fi

extra_args=()
if [[ "$dry_run" == "--dry-run" ]]; then
  extra_args+=(--dry-run)
fi

case "$command_name" in
  upload)
    for directory in data artifacts; do
      rclone copy "$repo_root/$directory" "$destination/$directory" \
        --fast-list --transfers 16 --progress "${extra_args[@]}"
    done
    ;;
  download)
    for directory in data artifacts; do
      mkdir -p "$repo_root/$directory"
      rclone copy "$destination/$directory" "$repo_root/$directory" \
        --fast-list --transfers 16 --progress "${extra_args[@]}"
    done
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
