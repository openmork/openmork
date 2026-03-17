# T10 — Observabilidad y taxonomía de errores (core)

## Alcance implementado

Se introdujo una taxonomía explícita para errores de runtime en `core/agent_runtime/error_taxonomy.py`:

- `api_call_interrupted`
- `api_call_failed`
- `api_stream_failed`
- `tool_invoke_failed`
- `tool_result_error`
- `checkpoint_presave_failed`

Cada evento se emite como JSON estructurado con:

- `ts`
- `code`
- `severity`
- `message`
- `context`

## Integración

Se conectó en puntos críticos del runtime:

- `core/agent_runtime/api_client_helpers.py`
  - fallos de llamada API
  - fallos de stream
  - fallos de cleanup en interrupción
- `core/agent_runtime/tool_execution.py`
  - fallos de invoke
  - resultados de herramienta marcados como error
  - fallos de pre-checkpoint

## Compatibilidad

- No cambia contratos públicos de tool calls.
- Se mantiene comportamiento funcional previo.
- Se añade solo señal observacional estructurada.

## Validación

- Nuevo test: `tests/test_error_taxonomy.py` (2 tests)
- Resultado local: `2 passed`
