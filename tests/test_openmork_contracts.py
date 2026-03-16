import pytest

from openmork_contracts import ArmContractError, validate_arm_contract


class _GoodGateway:
    apiVersion = "1.0"

    def start(self):
        return None

    def stop(self):
        return None

    def send_message(self, session_id: str, content: str, **kwargs):
        return True

    def register_callback(self, handler):
        return None


class _BadGateway:
    def start(self):
        return None


def test_validate_arm_contract_accepts_valid_gateway_arm():
    validate_arm_contract(_GoodGateway(), arm_kind="gateway")


def test_validate_arm_contract_rejects_missing_api_and_methods():
    with pytest.raises(ArmContractError) as exc:
        validate_arm_contract(_BadGateway(), arm_kind="gateway")
    message = str(exc.value)
    assert "missing required API" in message or "missing required 'apiVersion'" in message
