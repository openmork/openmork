# T6 DONE — tipado progresivo core (strict por perímetro)

## Cambios
- `pyproject.toml`
  - añadido `mypy` en dev
  - configurado `[tool.mypy]` strict para perímetro core:
    - `core/agent_runtime/runtime_context.py`
    - `core/agent_runtime/conversation_utils.py`
    - `core/agent_runtime/io_safety.py`
    - `core/agent_runtime/error_taxonomy.py`
- `.github/workflows/tests.yml`
  - nuevo paso CI: `python -m mypy`
- Tipado reforzado en `runtime_context.py` e `io_safety.py`

## Evidencias
- `python -m mypy` → PASS

## Riesgos
- Cobertura de typing aún parcial (perímetro inicial), no repo completo.
