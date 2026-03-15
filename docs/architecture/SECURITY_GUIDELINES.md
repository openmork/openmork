# OpenMork Security Guidelines

**Version:** 1.0

This document outlines the mandatory security practices for OpenMork operators and Arm developers. Security in OpenMork is "Controllable", meaning the user always has the final say, but the defaults must be strictly secure.

## 1. Secrets Management
Never hardcode tokens or API keys anywhere in the codebase.
- Always use the `.env` file or native Keychain/Credential Managers.
- The `.gitignore` file enforces that no `.env` files (except `.env.example`) or `.key`/`.pem` files are committed.
- Remote Git URLs MUST NEVER contain inline tokens (`https://ghp_xxx@github...`). Always use SSH or a Git Credential Manager.

## 2. The Security Arm (`BaseSecurityFilter`)
The default security arm uses pattern matching (`safety.yaml`) to intercept dangerous actions.
- **Warn-Only by Default:** The agent should pause and ask the user for permission (`[o]nce/[s]ession/[d]eny`) instead of silently failing.
- **YOLO Mode:** If `OPENMORK_YOLO_MODE` is set, all checks are bypassed. This is for restricted sandbox environments only.

## 3. Network and Filesystem Isolation
Arms should assume they are running in a hostile environment if exposed to the internet.
- **Filesystem:** Do not allow arbitrary read/writes outside the defined workspace without explicit approval.
- **Network:** Gateway modules should validate webhook signatures and sanitize all incoming payloads.

## 4. Automated operational checks (required)
OpenMork ships a repo scanner at `scripts/security/check_secrets.py`.

It blocks commits/CI when it detects:
- likely secrets/tokens in files (OpenAI, Anthropic, GitHub PAT, AWS access key IDs, generic token assignments)
- git remotes with embedded credentials in URL, e.g. `https://<secret>@github.com/org/repo.git`

Run locally:
```bash
python scripts/security/check_secrets.py          # staged files + remotes
python scripts/security/check_secrets.py --all-files
```

Install the local git hook:
```bash
ln -sf ../../scripts/security/pre-commit .git/hooks/pre-commit
```

CI also runs this check on pushes and pull requests via `.github/workflows/security-check.yml`.
