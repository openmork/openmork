import pytest
from abc import ABC, abstractmethod

# Simulación de los contratos ARM extraídos de ARM_CONTRACTS.md
class BaseGateway(ABC):
    @abstractmethod
    def start(self) -> None: pass
    
    @abstractmethod
    def stop(self) -> None: pass

class BaseMemoryProvider(ABC):
    @abstractmethod
    def get_session_state(self, session_id: str) -> dict: pass

def test_gateway_contract_enforcement():
    class InvalidGateway(BaseGateway):
        def start(self): pass
        # Falta stop()
        
    with pytest.raises(TypeError):
        InvalidGateway()
        
def test_valid_memory_provider():
    class ValidMemory(BaseMemoryProvider):
        def get_session_state(self, session_id): return {}
    
    mem = ValidMemory()
    assert mem.get_session_state("123") == {}
