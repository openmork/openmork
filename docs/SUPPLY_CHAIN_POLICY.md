# Supply-chain policy (T8 MVP)

## Download trust policy

All automatic archive downloads in update flows must:

1. Use HTTPS only.
2. Use an allowlisted host (`github.com`, `codeload.github.com`, `raw.githubusercontent.com`).
3. Reject archives with path traversal entries (zip-slip prevention).

## Implemented guards

- `openmork_cli/supply_chain.py`
  - `ensure_trusted_download_url(url)`
  - `safe_extract_zip(zip_path, dest_dir)`
- `openmork_cli/main.py::_update_via_zip()` now enforces both checks.

## Security tests

- `tests/openmork_cli/test_supply_chain.py`
  - blocks non-HTTPS and non-allowlisted hosts
  - blocks `../` zip-slip entries
  - allows normal GitHub archive extraction
