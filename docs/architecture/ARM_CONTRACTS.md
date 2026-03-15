# OpenMork Core Protocol: ARM Contracts

**Version:** 1.0 (Draft)
**Status:** Alpha

OpenMork is built around the concept of "Arms" (swappable modules). To prevent the platform from becoming a "Frankenstack" and to ensure community extensions remain compatible over time, all Arms MUST implement the following strict contracts.

Prs that add new functionality without adhering to these contracts will be rejected.

## The 4 Pillars of OpenMork

Every openmork instance is composed of four primary Arms:

1. **Gateway** (`BaseGateway`): Handles I/O with the outside world (Telegram, CLI, Discord, etc.)
2. **Memory** (`BaseMemoryProvider`): Handles persistence and retrieval of state, context, and semantic data.
3. **Security** (`BaseSecurityFilter`): Intercepts and validates actions before execution.
4. **Skills** (`BaseSkillset`): Defines the capabilities the agent possesses.

---

### 1. Gateway Interface (`BaseGateway`)

A Gateway is responsible for receiving events (e.g., messages) and passing them to the core loop, and for rendering the agent's output back to the platform.

**Required Methods (Python ABC):**
```python
class BaseGateway(ABC):
    @abstractmethod
    def start(self) -> None:
        """Initialize connection to the platform."""
        pass
        
    @abstractmethod
    def stop(self) -> None:
        """Gracefully disconnect."""
        pass

    @abstractmethod
    def send_message(self, session_id: str, content: str, **kwargs) -> bool:
        """Send text to the user/platform."""
        pass
        
    @abstractmethod
    def register_callback(self, handler: Callable[[Event], None]) -> None:
        """Register the core agent loop to receive incoming events."""
        pass
```

### 2. Memory Interface (`BaseMemoryProvider`)

The Memory Arm abstracts the underlying database (SQLite, Postgres/pgvector, etc.). It must support both key-value storage (for state) and semantic search (for rag).

**Required Methods (Python ABC):**
```python
class BaseMemoryProvider(ABC):
    @abstractmethod
    def get_session_state(self, session_id: str) -> dict:
        """Retrieve state variables for the session."""
        pass
        
    @abstractmethod
    def save_session_state(self, session_id: str, state: dict) -> None:
        """Persist state updates."""
        pass
        
    @abstractmethod
    def add_memory(self, content: str, metadata: dict = None) -> str:
        """Store a semantic memory and return its ID."""
        pass
        
    @abstractmethod
    def search_memories(self, query: str, limit: int = 5) -> List[dict]:
        """Perform semantic search over memories."""
        pass
```


### 3. Security Interface (`BaseSecurityFilter`)

The Security Arm validates tool executions and system commands before they are delegated to the OS.

**Required Methods (Python ABC):**
```python
class BaseSecurityFilter(ABC):
    @abstractmethod
    def validate_action(self, action_type: str, payload: dict, context: dict) -> ValidationResult:
        """
        Evaluate if an action is safe.
        Returns a ValidationResult(is_allowed: bool, reason: str, requires_approval: bool)
        """
        pass
```


### 4. Skillset Interface (`BaseSkillset`)

Skills define the agent's toolbelt. A skillset groups related tools and provides them dynamically.

**Required Methods (Python ABC):**
```python
class BaseSkillset(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> List[ToolDefinition]:
        """List the tools registered in this skillset."""
        pass

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict) -> Any:
        """Execute the requested tool."""
        pass
```

---

## Compatibility Guidelines

- **Semantic Versioning:** Arms must declare compatibility against the OpenMork Core Protocol version (e.g., `openmork_api: "1.0"`).
- **Graceful Degradation:** If a feature is not supported by a platform (e.g., Markdown in SMS), the Gateway must degrade gracefully, not crash.
- **Stateless Core:** The OpenMork core loop assumes all state is managed by the `BaseMemoryProvider`. Arms must not leak internal state across sessions.
