# Dependency source of truth (T7)

Openmork uses a **single canonical dependency source**:

- `pyproject.toml` → declared dependencies
- `uv.lock` → pinned, reproducible lockfile for CI/release

`requirements.txt` is legacy/convenience only and must not become the primary source.

## Official install/update flow

### Fresh install (dev)

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[all,dev]"
```

### Update lockfile after dependency changes

```bash
# after editing pyproject.toml
uv lock
uv pip sync uv.lock
```

### CI integrity checks

- `scripts/security/check_dependency_integrity.py --lock uv.lock`
- Security workflow runs lock integrity guardrails

## Policy

1. Add/change dependencies only in `pyproject.toml`.
2. Regenerate and commit `uv.lock` in the same PR.
3. Do not add unpinned editable third-party deps to the lock.
4. Keep `requirements.txt` comments aligned, but treat it as non-canonical.
