# B2 Storage and Recovery

This guide owns Backblaze B2 snapshot setup, synchronization, safety, recovery,
and authority-transfer procedures for Tradix `data/` and `artifacts/`.

## Prerequisites and Configuration

Install rclone and create a Backblaze B2 remote:

```sh
rclone config
```

Repository defaults expect remote `b2`, bucket `tradix-kumetix`, and prefix
`tradix/`. To use another location, copy `.b2.env.example` to `.b2.env` and edit
only the non-secret remote, bucket, and prefix settings.

Give the B2 application key access only to the intended bucket and prefix.
Credentials belong in rclone's per-user configuration. Never store credentials
in `.b2.env` or Git.

## Initialize a Clone

Initialize a clone and, on a supported Linux user session, enable the automatic
15-minute mirror:

```sh
scripts/setup-b2-sync.sh
```

The setup verifies that the remote is nonempty, downloads `data/` and
`artifacts/`, verifies the snapshot, records the canonical-row inventory, and
marks the clone as initialized.

Restore a clone without making it an automatic mirror:

```sh
scripts/setup-b2-sync.sh --no-timer
```

Only one computer should run the authoritative timer at a time.

## Safety Model

An initialized authoritative clone mirrors local `data/` and `artifacts/` to
B2, including artifact deletions. Before changing B2, synchronization:

- verifies initialization and a nonempty remote;
- compares the canonical-row inventory;
- detects deleted canonical price or analyst rows;
- attempts to refetch missing source data;
- regenerates affected features;
- aborts without changing B2 when repair is incomplete; and
- enforces a maximum deletion limit.

These controls protect a fresh, empty, or damaged clone from overwriting the
shared snapshot. They do not replace scoped B2 credentials or the single-authority
rule.

## Verify and Reconcile

Verify local and remote state:

```sh
scripts/b2-storage.sh verify
```

Reconcile an initialized authoritative clone manually:

```sh
scripts/b2-storage.sh reconcile
```

Preview transfers and inspect stored objects before a material change:

```sh
scripts/b2-storage.sh reconcile --dry-run
scripts/b2-storage.sh list
```

Never rely on a temporary fetched CSV as repaired canonical data. Price rows
must be persisted under `data/stock/prices/daily/<year>/<ticker>.csv`, analyst
rows under their canonical dataset, and dependent feature files regenerated
before reconciliation.

## Monitor Automatic Mirroring

Inspect the user timer and recent service logs:

```sh
systemctl --user status tradix-b2-sync.timer
journalctl --user -u tradix-b2-sync.service
```

Stop automatic mirroring before maintenance that should not be propagated:

```sh
systemctl --user disable --now tradix-b2-sync.timer
```

## Transfer Authority

On the old authoritative computer:

```sh
systemctl --user disable --now tradix-b2-sync.timer
scripts/b2-storage.sh reconcile
scripts/b2-storage.sh verify
```

After the final reconciliation succeeds, initialize the new computer with
`scripts/setup-b2-sync.sh` and confirm that its timer is the only authoritative
timer enabled. Do not enable both machines concurrently.

## Recovery Rules

- Run `verify` before and after recovery work.
- Prefer refetching canonical source rows and regenerating derived features over
  copying partial temporary files.
- Use `--dry-run` before reconciliation when deletion or repair scope is
  uncertain.
- Do not bypass initialization, nonempty-remote, repair, or deletion-limit
  failures merely to force a mirror.
- Preserve generated artifacts only when they remain meaningful research
  records; artifact deletion by the authority propagates to B2.
