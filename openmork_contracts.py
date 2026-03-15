"""Runtime contracts for OpenMork Arms.

These checks are intentionally lightweight and runtime-oriented:
- enforce a minimal API surface for each arm type
- enforce a compatible ``apiVersion`` value
- produce actionable exceptions for operators

Legacy compatibility: callers may set ``allow_legacy_api_version=True`` to
accept arms missing ``apiVersion`` and treat them as ``1.0``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Protocol, runtime_checkable


class ArmContractError(ValueError):
    """Raised when an arm does not satisfy the runtime contract."""


@dataclass(frozen=True)
class ValidationResult:
    is_allowed: bool
    reason: str = ""
    requires_approval: bool = False


class _HasApiVersion(Protocol):
    apiVersion: str


class GatewayArm(ABC):
    apiVersion: str

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def send_message(self, session_id: str, content: str, **kwargs: Any) -> bool:
        ...

    @abstractmethod
    def register_callback(self, handler: Any) -> None:
        ...


class MemoryArm(ABC):
    apiVersion: str

    @abstractmethod
    def get_session_state(self, session_id: str) -> dict:
        ...

    @abstractmethod
    def save_session_state(self, session_id: str, state: dict) -> None:
        ...

    @abstractmethod
    def add_memory(self, content: str, metadata: Optional[dict] = None) -> str:
        ...

    @abstractmethod
    def search_memories(self, query: str, limit: int = 5) -> list[dict]:
        ...


class SecurityArm(ABC):
    apiVersion: str

    @abstractmethod
    def validate_action(self, action_type: str, payload: dict, context: dict) -> ValidationResult:
        ...


class SkillsetArm(ABC):
    apiVersion: str

    @property
    @abstractmethod
    def capabilities(self) -> list[Any]:
        ...

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict) -> Any:
        ...


@runtime_checkable
class GatewayArmProtocol(Protocol):
    apiVersion: str
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def send_message(self, session_id: str, content: str, **kwargs: Any) -> bool: ...
    def register_callback(self, handler: Any) -> None: ...


@runtime_checkable
class MemoryArmProtocol(Protocol):
    apiVersion: str
    def get_session_state(self, session_id: str) -> dict: ...
    def save_session_state(self, session_id: str, state: dict) -> None: ...
    def add_memory(self, content: str, metadata: Optional[dict] = None) -> str: ...
    def search_memories(self, query: str, limit: int = 5) -> list[dict]: ...


@runtime_checkable
class SecurityArmProtocol(Protocol):
    apiVersion: str
    def validate_action(self, action_type: str, payload: dict, context: dict) -> ValidationResult: ...


@runtime_checkable
class SkillsetArmProtocol(Protocol):
    apiVersion: str
    @property
    def capabilities(self) -> list[Any]: ...
    def execute(self, tool_name: str, arguments: dict) -> Any: ...


def _missing_methods(arm: Any, required: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for name in required:
        candidate = getattr(arm, name, None)
        if not callable(candidate):
            missing.append(name)
    return missing


def validate_arm_contract(
    arm: Any,
    expected_api_version: str = "1.0",
    arm_kind: Optional[str] = None,
    allow_legacy_api_version: bool = False,
) -> None:
    """Validate a runtime arm instance against the OpenMork ARM contract.

    Args:
        arm: Runtime object to validate.
        expected_api_version: Required protocol version.
        arm_kind: One of ``gateway``, ``memory``, ``security``, ``skillset``.
            If omitted, method-based auto-detection is used.
        allow_legacy_api_version: If True, missing ``apiVersion`` is tolerated
            and considered ``expected_api_version`` for backward compatibility.

    Raises:
        ArmContractError: if validation fails.
    """
    if arm is None:
        raise ArmContractError("Arm contract validation failed: arm instance is None.")

    kind_to_methods = {
        "gateway": ("start", "stop", "send_message", "register_callback"),
        "memory": ("get_session_state", "save_session_state", "add_memory", "search_memories"),
        "security": ("validate_action",),
        "skillset": ("execute",),
    }

    if arm_kind is None:
        for candidate_kind, methods in kind_to_methods.items():
            if not _missing_methods(arm, methods):
                arm_kind = candidate_kind
                break

    if arm_kind not in kind_to_methods:
        known = ", ".join(sorted(kind_to_methods))
        raise ArmContractError(
            f"Unknown arm kind '{arm_kind}'. Expected one of: {known}. "
            "Pass arm_kind explicitly when registering custom arms."
        )

    required_methods = kind_to_methods[arm_kind]
    missing = _missing_methods(arm, required_methods)
    if arm_kind == "skillset" and getattr(arm, "capabilities", None) is None:
        missing.append("capabilities")
    if missing:
        raise ArmContractError(
            f"{arm_kind.capitalize()}Arm contract validation failed for "
            f"{arm.__class__.__name__}: missing required API {missing}. "
            "Implement the methods/properties from docs/architecture/ARM_CONTRACTS.md."
        )

    api_version = getattr(arm, "apiVersion", None)
    if not api_version:
        if allow_legacy_api_version:
            setattr(arm, "apiVersion", expected_api_version)
            api_version = expected_api_version
        else:
            raise ArmContractError(
                f"{arm_kind.capitalize()}Arm contract validation failed for {arm.__class__.__name__}: "
                "missing required 'apiVersion' attribute. Add apiVersion='1.0' "
                "(or pass allow_legacy_api_version=True during transitional loading)."
            )

    if str(api_version) != str(expected_api_version):
        raise ArmContractError(
            f"{arm_kind.capitalize()}Arm contract validation failed for {arm.__class__.__name__}: "
            f"apiVersion='{api_version}' is incompatible with expected '{expected_api_version}'. "
            "Upgrade the arm or pin a compatible expected_api_version."
        )
