import pytest

class ArmRegistry:
    def __init__(self):
        self._arms = {}
        
    def register(self, name, arm_instance):
        self._arms[name] = arm_instance
        
    def get(self, name):
        return self._arms.get(name)

def test_registry_registration():
    registry = ArmRegistry()
    registry.register("gateway", "mock_gateway_instance")
    
    assert registry.get("gateway") == "mock_gateway_instance"
    assert registry.get("memory") is None
