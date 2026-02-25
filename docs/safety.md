# Safety First

`fsweep` is built with a robust safety-first model to ensure your source code
stays safe while you're cleaning up.

## 🛡️ Safety Model

- **Default Mode**: Non-destructive (`--dry-run`). `fsweep` will never delete
  anything by default.
- **Destructive Runs**: Requires `--delete --yes-delete`.
- **System-level Protection**: `fsweep` refuses to sweep the root (`/`) or
  your home directory root.
- **Deletion Limit**: Destructive runs are capped by `--max-delete-count`
  (default 50) to prevent accidental large-scale deletions. You can override
  this with `--no-delete-limit`.

## ⚖️ Dry-run Parity Guarantee

`fsweep` includes a dry-run parity test that guarantees the matched set in
dry-run and destructive mode is identical for equivalent flags and path.

## 🗑️ Trash Mode

Optional `--trash` mode is destructive but recoverable. It moves matched
folders to `~/.fsweep_trash` instead of permanently deleting them.

```bash
uv run fsweep --delete --trash --yes-delete
```

This is the safest way to perform a destructive run, allowing you to recover
any folders that were accidentally trashed.
