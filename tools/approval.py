"""Dangerous command approval -- detection, prompting, and per-session state.

This module is the single source of truth for the dangerous command system:
- Pattern detection (DANGEROUS_PATTERNS, detect_dangerous_command)
- Per-session approval state (thread-safe, keyed by session_key)
- Approval prompting (CLI interactive + gateway async)
- Permanent allowlist persistence (config.yaml)
"""

import logging
import os
import re
import sys
import threading
from typing import Optional

from openmork_contracts import ValidationResult, validate_arm_contract

logger = logging.getLogger(__name__)

# =========================================================================
# Dangerous command patterns — loaded from ~/.openmork/safety.yaml
# =========================================================================

_DEFAULT_PATTERNS = [
    (r'\brm\s+(-[^\s]*\s+)*/', "delete in root path"),
    (r'\brm\s+-[^\s]*r', "recursive delete"),
    (r'\brm\s+--recursive\b', "recursive delete (long flag)"),
    (r'\bchmod\s+(-[^\s]*\s+)*777\b', "world-writable permissions"),
    (r'\bchmod\s+--recursive\b.*777', "recursive world-writable (long flag)"),
    (r'\bchown\s+(-[^\s]*)?R\s+root', "recursive chown to root"),
    (r'\bchown\s+--recursive\b.*root', "recursive chown to root (long flag)"),
    (r'\bmkfs\b', "format filesystem"),
    (r'\bdd\s+.*if=', "disk copy"),
    (r'>\s*/dev/sd', "write to block device"),
    (r'\bDROP\s+(TABLE|DATABASE)\b', "SQL DROP"),
    (r'\bDELETE\s+FROM\b(?!.*\bWHERE\b)', "SQL DELETE without WHERE"),
    (r'\bTRUNCATE\s+(TABLE)?\s*\w', "SQL TRUNCATE"),
    (r'>\s*/etc/', "overwrite system config"),
    (r'\bsystemctl\s+(stop|disable|mask)\b', "stop/disable system service"),
    (r'\bkill\s+-9\s+-1\b', "kill all processes"),
    (r'\bpkill\s+-9\b', "force kill processes"),
    (r':\(\)\s*\{\s*:\s*\|\s*:\s*\&\s*\}\s*;\s*:', "fork bomb"),
    (r'\b(bash|sh|zsh)\s+-c\s+', "shell command via -c flag"),
    (r'\b(python[23]?|perl|ruby|node)\s+-[ec]\s+', "script execution via -e/-c flag"),
    (r'\b(curl|wget)\b.*\|\s*(ba)?sh\b', "pipe remote content to shell"),
    (r'\b(bash|sh|zsh|ksh)\s+<\s*<?\s*\(\s*(curl|wget)\b', "execute remote script via process substitution"),
    (r'\btee\b.*(/etc/|/dev/sd|\.ssh/|\.openmork/\.env)', "overwrite system file via tee"),
    (r'\bxargs\s+.*\brm\b', "xargs with rm"),
    (r'\bfind\b.*-exec\s+(/\S*/)?rm\b', "find -exec rm"),
    (r'\bfind\b.*-delete\b', "find -delete"),
]


def _load_safety_yaml() -> list:
    """Load dangerous command patterns from ~/.openmork/safety.yaml.

    Falls back to built-in defaults if the file doesn't exist or is invalid.
    The YAML format is:
        dangerous_patterns:
          - pattern: '\\brm\\s+-[^\\s]*r'
            description: "recursive delete"
          - pattern: ...
    """
    openmork_home = os.getenv("OPENMORK_HOME", os.path.expanduser("~/.openmork"))
    safety_path = os.path.join(openmork_home, "safety.yaml")

    if not os.path.isfile(safety_path):
        return list(_DEFAULT_PATTERNS)

    try:
        import yaml
    except ImportError:
        logger.debug("PyYAML not installed, using default patterns")
        return list(_DEFAULT_PATTERNS)

    try:
        with open(safety_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        raw_patterns = config.get("dangerous_patterns", None)
        if raw_patterns is None:
            return list(_DEFAULT_PATTERNS)

        patterns = []
        for entry in raw_patterns:
            if isinstance(entry, dict) and "pattern" in entry and "description" in entry:
                patterns.append((entry["pattern"], entry["description"]))
            else:
                logger.warning("Skipping malformed pattern entry in safety.yaml: %s", entry)
        
        if not patterns:
            logger.warning("No valid patterns in safety.yaml, using defaults")
            return list(_DEFAULT_PATTERNS)

        logger.info("Loaded %d dangerous command patterns from %s", len(patterns), safety_path)
        return patterns

    except Exception as e:
        logger.warning("Failed to load safety.yaml (%s), using defaults", e)
        return list(_DEFAULT_PATTERNS)


DANGEROUS_PATTERNS = _load_safety_yaml()


def _legacy_pattern_key(pattern: str) -> str:
    """Reproduce the old regex-derived approval key for backwards compatibility."""
    return pattern.split(r'\b')[1] if r'\b' in pattern else pattern[:20]


_PATTERN_KEY_ALIASES: dict[str, set[str]] = {}
for _pattern, _description in DANGEROUS_PATTERNS:
    _legacy_key = _legacy_pattern_key(_pattern)
    _canonical_key = _description
    _PATTERN_KEY_ALIASES.setdefault(_canonical_key, set()).update({_canonical_key, _legacy_key})
    _PATTERN_KEY_ALIASES.setdefault(_legacy_key, set()).update({_legacy_key, _canonical_key})


def _approval_key_aliases(pattern_key: str) -> set[str]:
    """Return all approval keys that should match this pattern.

    New approvals use the human-readable description string, but older
    command_allowlist entries and session approvals may still contain the
    historical regex-derived key.
    """
    return _PATTERN_KEY_ALIASES.get(pattern_key, {pattern_key})


# =========================================================================
# Detection
# =========================================================================

def detect_dangerous_command(command: str) -> tuple:
    """Check if a command matches any dangerous patterns.

    Returns:
        (is_dangerous, pattern_key, description) or (False, None, None)
    """
    command_lower = command.lower()
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, command_lower, re.IGNORECASE | re.DOTALL):
            pattern_key = description
            return (True, pattern_key, description)
    return (False, None, None)


# =========================================================================
# Per-session approval state (thread-safe)
# =========================================================================

_lock = threading.Lock()
_pending: dict[str, dict] = {}
_session_approved: dict[str, set] = {}
_permanent_approved: set = set()


def submit_pending(session_key: str, approval: dict):
    """Store a pending approval request for a session."""
    with _lock:
        _pending[session_key] = approval


def pop_pending(session_key: str) -> Optional[dict]:
    """Retrieve and remove a pending approval for a session."""
    with _lock:
        return _pending.pop(session_key, None)


def has_pending(session_key: str) -> bool:
    """Check if a session has a pending approval request."""
    with _lock:
        return session_key in _pending


def approve_session(session_key: str, pattern_key: str):
    """Approve a pattern for this session only."""
    with _lock:
        _session_approved.setdefault(session_key, set()).add(pattern_key)


def is_approved(session_key: str, pattern_key: str) -> bool:
    """Check if a pattern is approved (session-scoped or permanent).

    Accept both the current canonical key and the legacy regex-derived key so
    existing command_allowlist entries continue to work after key migrations.
    """
    aliases = _approval_key_aliases(pattern_key)
    with _lock:
        if any(alias in _permanent_approved for alias in aliases):
            return True
        session_approvals = _session_approved.get(session_key, set())
        return any(alias in session_approvals for alias in aliases)


def approve_permanent(pattern_key: str):
    """Add a pattern to the permanent allowlist."""
    with _lock:
        _permanent_approved.add(pattern_key)


def load_permanent(patterns: set):
    """Bulk-load permanent allowlist entries from config."""
    with _lock:
        _permanent_approved.update(patterns)


def clear_session(session_key: str):
    """Clear all approvals and pending requests for a session."""
    with _lock:
        _session_approved.pop(session_key, None)
        _pending.pop(session_key, None)


# =========================================================================
# Config persistence for permanent allowlist
# =========================================================================

def load_permanent_allowlist() -> set:
    """Load permanently allowed command patterns from config.

    Also syncs them into the approval module so is_approved() works for
    patterns added via 'always' in a previous session.
    """
    try:
        from openmork_cli.config import load_config
        config = load_config()
        patterns = set(config.get("command_allowlist", []) or [])
        if patterns:
            load_permanent(patterns)
        return patterns
    except Exception:
        return set()


def save_permanent_allowlist(patterns: set):
    """Save permanently allowed command patterns to config."""
    try:
        from openmork_cli.config import load_config, save_config
        config = load_config()
        config["command_allowlist"] = list(patterns)
        save_config(config)
    except Exception as e:
        logger.warning("Could not save allowlist: %s", e)


# =========================================================================
# Approval prompting + orchestration
# =========================================================================

def prompt_dangerous_approval(command: str, description: str,
                              timeout_seconds: int = 60,
                              allow_permanent: bool = True,
                              approval_callback=None) -> str:
    """Prompt the user to approve a dangerous command (CLI only).

    Args:
        allow_permanent: When False, hide the [a]lways option (used when
            tirith warnings are present, since broad permanent allowlisting
            is inappropriate for content-level security findings).
        approval_callback: Optional callback registered by the CLI for
            prompt_toolkit integration. Signature:
            (command, description, *, allow_permanent=True) -> str.

    Returns: 'once', 'session', 'always', or 'deny'
    """
    if approval_callback is not None:
        try:
            return approval_callback(command, description,
                                     allow_permanent=allow_permanent)
        except Exception:
            return "deny"

    os.environ["OPENMORK_SPINNER_PAUSE"] = "1"
    try:
        is_truncated = len(command) > 80
        while True:
            print()
            print(f"  ⚠️  DANGEROUS COMMAND: {description}")
            print(f"      {command[:80]}{'...' if is_truncated else ''}")
            print()
            view_hint = "  |  [v]iew full" if is_truncated else ""
            if allow_permanent:
                print(f"      [o]nce  |  [s]ession  |  [a]lways  |  [d]eny{view_hint}")
            else:
                print(f"      [o]nce  |  [s]ession  |  [d]eny{view_hint}")
            print()
            sys.stdout.flush()

            result = {"choice": ""}

            def get_input():
                try:
                    prompt = "      Choice [o/s/a/D]: " if allow_permanent else "      Choice [o/s/D]: "
                    result["choice"] = input(prompt).strip().lower()
                except (EOFError, OSError):
                    result["choice"] = ""

            thread = threading.Thread(target=get_input, daemon=True)
            thread.start()
            thread.join(timeout=timeout_seconds)

            if thread.is_alive():
                print("\n      ⏱ Timeout - denying command")
                return "deny"

            choice = result["choice"]
            if choice in ('v', 'view') and is_truncated:
                print()
                print("      Full command:")
                print(f"      {command}")
                is_truncated = False
                continue
            if choice in ('o', 'once'):
                print("      ✓ Allowed once")
                return "once"
            elif choice in ('s', 'session'):
                print("      ✓ Allowed for this session")
                return "session"
            elif choice in ('a', 'always'):
                if not allow_permanent:
                    print("      ✓ Allowed for this session")
                    return "session"
                print("      ✓ Added to permanent allowlist")
                return "always"
            else:
                print("      ✗ Denied")
                return "deny"

    except (EOFError, KeyboardInterrupt):
        print("\n      ✗ Cancelled")
        return "deny"
    finally:
        if "OPENMORK_SPINNER_PAUSE" in os.environ:
            del os.environ["OPENMORK_SPINNER_PAUSE"]
        print()
        sys.stdout.flush()


def check_dangerous_command(command: str, env_type: str,
                            approval_callback=None) -> dict:
    """Check if a command is dangerous and handle approval.

    This is the main entry point called by terminal_tool before executing
    any command. It orchestrates detection, session checks, and prompting.

    Args:
        command: The shell command to check.
        env_type: Terminal backend type ('local', 'ssh', 'docker', etc.).
        approval_callback: Optional CLI callback for interactive prompts.

    Returns:
        {"approved": True/False, "message": str or None, ...}
    """
    if env_type in ("docker", "singularity", "modal", "daytona"):
        return {"approved": True, "message": None}

    # Hard deny mode (e.g. production lockdown)
    if (os.getenv("OPENMORK_TOOL_POLICY_MODE") or "").strip().lower() == "deny":
        return {
            "approved": False,
            "message": "BLOCKED: tool policy mode is 'deny' for this environment.",
            "status": "policy_denied",
        }

    # --yolo: bypass all approval prompts
    if os.getenv("OPENMORK_YOLO_MODE"):
        return {"approved": True, "message": None}

    is_dangerous, pattern_key, description = detect_dangerous_command(command)
    if not is_dangerous:
        return {"approved": True, "message": None}

    session_key = os.getenv("OPENMORK_SESSION_KEY", "default")
    if is_approved(session_key, pattern_key):
        return {"approved": True, "message": None}

    is_cli = os.getenv("OPENMORK_INTERACTIVE")
    is_gateway = os.getenv("OPENMORK_GATEWAY_SESSION")

    if not is_cli and not is_gateway:
        return {"approved": True, "message": None}

    if is_gateway or os.getenv("OPENMORK_EXEC_ASK"):
        submit_pending(session_key, {
            "command": command,
            "pattern_key": pattern_key,
            "description": description,
        })
        return {
            "approved": False,
            "pattern_key": pattern_key,
            "status": "approval_required",
            "command": command,
            "description": description,
            "message": f"⚠️ This command is potentially dangerous ({description}). Asking the user for approval...",
        }

    choice = prompt_dangerous_approval(command, description,
                                       approval_callback=approval_callback)

    if choice == "deny":
        return {
            "approved": False,
            "message": f"BLOCKED: User denied this potentially dangerous command (matched '{description}' pattern). Do NOT retry this command - the user has explicitly rejected it.",
            "pattern_key": pattern_key,
            "description": description,
        }

    if choice == "session":
        approve_session(session_key, pattern_key)
    elif choice == "always":
        approve_session(session_key, pattern_key)
        approve_permanent(pattern_key)
        save_permanent_allowlist(_permanent_approved)

    return {"approved": True, "message": None}


# =========================================================================
# Combined pre-exec guard (tirith + dangerous command detection)
# =========================================================================

def check_all_command_guards(command: str, env_type: str,
                             approval_callback=None) -> dict:
    """Run all pre-exec security checks and return a single approval decision.

    Gathers findings from tirith and dangerous-command detection, then
    presents them as a single combined approval request. This prevents
    a gateway force=True replay from bypassing one check when only the
    other was shown to the user.
    """
    # Skip containers for both checks
    if env_type in ("docker", "singularity", "modal", "daytona"):
        return {"approved": True, "message": None}

    # Hard deny mode (e.g. production lockdown)
    if (os.getenv("OPENMORK_TOOL_POLICY_MODE") or "").strip().lower() == "deny":
        return {
            "approved": False,
            "message": "BLOCKED: tool policy mode is 'deny' for this environment.",
            "status": "policy_denied",
        }

    # --yolo: bypass all approval prompts and pre-exec guard checks
    if os.getenv("OPENMORK_YOLO_MODE"):
        return {"approved": True, "message": None}

    is_cli = os.getenv("OPENMORK_INTERACTIVE")
    is_gateway = os.getenv("OPENMORK_GATEWAY_SESSION")
    is_ask = os.getenv("OPENMORK_EXEC_ASK")

    # Preserve the existing non-interactive behavior: outside CLI/gateway/ask
    # flows, we do not block on approvals and we skip external guard work.
    if not is_cli and not is_gateway and not is_ask:
        return {"approved": True, "message": None}

    # --- Phase 1: Gather findings from both checks ---

    # Tirith check — wrapper guarantees no raise for expected failures.
    # Only catch ImportError (module not installed).
    tirith_result = {"action": "allow", "findings": [], "summary": ""}
    try:
        from tools.tirith_security import check_command_security
        tirith_result = check_command_security(command)
    except ImportError:
        pass  # tirith module not installed — allow

    # Dangerous command check (detection only, no approval)
    is_dangerous, pattern_key, description = detect_dangerous_command(command)

    # --- Phase 2: Decide ---

    # Respect tirith "block" actions as hard blocks.

    session_key = os.getenv("OPENMORK_SESSION_KEY", "default")

    if tirith_result["action"] == "block":
        findings = tirith_result.get("findings") or []
        summary = tirith_result.get("summary") or "security policy violation"
        if findings:
            first = findings[0]
            rid = first.get("rule_id")
            sev = first.get("severity")
            parts = [p for p in [summary, rid, sev] if p]
            summary = " | ".join(parts)
        return {
            "approved": False,
            "message": f"BLOCKED: {summary}",
            "pattern_key": f"tirith:{(findings[0].get('rule_id') if findings else 'unknown')}",
            "description": summary,
        }

    # Collect warnings that need approval
    warnings = []  # list of (pattern_key, description, is_tirith)

    if tirith_result["action"] == "warn":
        findings = tirith_result.get("findings") or []
        rule_id = findings[0].get("rule_id", "unknown") if findings else "unknown"
        tirith_key = f"tirith:{rule_id}"
        tirith_desc = f"Security scan: {tirith_result.get('summary') or 'security warning detected'}"
        if not is_approved(session_key, tirith_key):
            warnings.append((tirith_key, tirith_desc, True))

    if is_dangerous:
        if not is_approved(session_key, pattern_key):
            warnings.append((pattern_key, description, False))

    # Nothing to warn about
    if not warnings:
        return {"approved": True, "message": None}

    # --- Phase 3: Approval ---

    # Combine descriptions for a single approval prompt
    combined_desc = "; ".join(desc for _, desc, _ in warnings)
    primary_key = warnings[0][0]
    all_keys = [key for key, _, _ in warnings]
    has_tirith = any(is_t for _, _, is_t in warnings)

    # Gateway/async: single approval_required with combined description
    # Store all pattern keys so gateway replay approves all of them
    if is_gateway or is_ask:
        submit_pending(session_key, {
            "command": command,
            "pattern_key": primary_key,        # backward compat
            "pattern_keys": all_keys,           # all keys for replay
            "description": combined_desc,
        })
        return {
            "approved": False,
            "pattern_key": primary_key,
            "status": "approval_required",
            "command": command,
            "description": combined_desc,
            "message": f"⚠️ {combined_desc}. Asking the user for approval...",
        }

    # CLI interactive: single combined prompt
    # Hide [a]lways when any tirith warning is present
    choice = prompt_dangerous_approval(command, combined_desc,
                                       allow_permanent=not has_tirith,
                                       approval_callback=approval_callback)

    if choice == "deny":
        return {
            "approved": False,
            "message": "BLOCKED: User denied. Do NOT retry.",
            "pattern_key": primary_key,
            "description": combined_desc,
        }

    # Persist approval for each warning individually
    for key, _, is_tirith in warnings:
        if choice == "session" or (choice == "always" and is_tirith):
            # tirith: session only (no permanent broad allowlisting)
            approve_session(session_key, key)
        elif choice == "always":
            # dangerous patterns: permanent allowed
            approve_session(session_key, key)
            approve_permanent(key)
            save_permanent_allowlist(_permanent_approved)

    return {"approved": True, "message": None}


class _DefaultSecurityArm:
    apiVersion = "1.0"

    def validate_action(self, action_type: str, payload: dict, context: dict) -> ValidationResult:
        if action_type != "terminal.command":
            return ValidationResult(is_allowed=True)

        command = str(payload.get("command", ""))
        approved = check_command_approval(command, session_key=str(context.get("session_key", "")))
        if approved.get("approved"):
            return ValidationResult(is_allowed=True)
        return ValidationResult(
            is_allowed=False,
            reason=str(approved.get("message") or approved.get("description") or "Approval required"),
            requires_approval=True,
        )




_DEFAULT_SECURITY_ARM = _DefaultSecurityArm()
validate_arm_contract(_DEFAULT_SECURITY_ARM, arm_kind="security", expected_api_version="1.0")


def get_default_security_arm() -> _DefaultSecurityArm:
    """Return the runtime security ARM used by terminal guard checks."""
    return _DEFAULT_SECURITY_ARM
