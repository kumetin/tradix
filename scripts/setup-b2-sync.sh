#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config_file="$repo_root/.b2.env"
example_config="$repo_root/.b2.env.example"
install_timer=true

if [[ "${1:-}" == "--no-timer" ]]; then
  install_timer=false
elif [[ $# -gt 0 ]]; then
  echo "Usage: scripts/setup-b2-sync.sh [--no-timer]" >&2
  exit 2
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "error: install rclone, then rerun this script" >&2
  echo "see https://rclone.org/install/" >&2
  exit 1
fi
if [[ "$install_timer" == true ]] && ! command -v flock >/dev/null 2>&1; then
  echo "error: flock is required for overlapping-run protection" >&2
  exit 1
fi

if [[ ! -f "$config_file" ]]; then
  install -m 600 "$example_config" "$config_file"
  echo "created $config_file from the repository defaults"
fi

# shellcheck disable=SC1090
source "$config_file"
remote="${TRADIX_B2_REMOTE:-b2}"

if ! rclone listremotes | grep -Fxq "${remote}:"; then
  echo "error: rclone remote '$remote' is not configured" >&2
  echo "run 'rclone config', create a Backblaze B2 remote named '$remote', then rerun this script" >&2
  exit 1
fi

"$repo_root/scripts/b2-storage.sh" bootstrap

if [[ "$install_timer" != true ]]; then
  echo "bootstrap complete; automatic reconciliation was not installed"
  exit 0
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "error: systemd is unavailable; rerun with --no-timer and configure your scheduler manually" >&2
  exit 1
fi

unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
rclone_dir="$(dirname "$(command -v rclone)")"
mkdir -p "$unit_dir"

cat > "$unit_dir/tradix-b2-sync.service" <<EOF
[Unit]
Description=Repair and mirror authoritative Tradix data and artifacts to Backblaze B2
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$repo_root
Environment=PATH=$rclone_dir:/usr/local/bin:/usr/bin:/bin
ExecStart=$repo_root/scripts/b2-storage.sh reconcile
Nice=10
EOF

cat > "$unit_dir/tradix-b2-sync.timer" <<'EOF'
[Unit]
Description=Repair and mirror authoritative Tradix data and artifacts to B2 every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
RandomizedDelaySec=1min
Persistent=true
Unit=tradix-b2-sync.service

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now tradix-b2-sync.timer
echo "bootstrap complete; tradix-b2-sync.timer is enabled"
