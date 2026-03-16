# T2 Progress — Split inicial de `run_agent.py`

Fecha: 2026-03-16

## Alcance de este corte (fase inicial)

Se ejecutó una extracción incremental y compatible hacia `core/agent_runtime/`:

1. **Runtime context / estado**
   - Nuevo módulo: `core/agent_runtime/runtime_context.py`
   - Extraído desde `run_agent.py`:
     - `IterationBudget`
     - `_inject_honcho_turn_context` (ahora `inject_honcho_turn_context`, re-exportado por alias en la fachada)

2. **Utilidades de ejecución/conversación**
   - Nuevo módulo: `core/agent_runtime/conversation_utils.py`
   - Extraído desde `run_agent.py`:
     - `_max_tokens_param` (lógica movida a `max_tokens_param`)
     - `_has_content_after_think_block` (lógica movida a `has_content_after_think_block`)
     - `_strip_think_blocks` (lógica movida a `strip_think_blocks`)
     - `_looks_like_codex_intermediate_ack` (lógica movida a `looks_like_codex_intermediate_ack`)
     - `_extract_reasoning` (lógica movida a `extract_reasoning_from_message`)

`run_agent.py` se mantiene como **fachada compatible** delegando a los nuevos helpers.

## Reducción inicial de tamaño

- LOC antes (`run_agent.py`): **6250**
- LOC después (`run_agent.py`): **6063**
- Reducción: **187 LOC**

## Validación rápida

Comandos ejecutados:

```bash
pytest -q -o addopts='' tests/test_agent_runtime_refactor_t2.py
python3 -m py_compile run_agent.py core/agent_runtime/runtime_context.py core/agent_runtime/conversation_utils.py
```

Resultado:
- `tests/test_agent_runtime_refactor_t2.py`: **3 passed**
- `py_compile`: **ok**

## Corte 2 (actual) — extracción adicional grande y cohesionada

Se completó una segunda extracción incremental centrada en:

1. **API client / provider call helpers**
   - Nuevo módulo: `core/agent_runtime/api_client_helpers.py`
   - Extraído desde `run_agent.py`:
     - `_interruptible_api_call`
     - `_streaming_api_call`
     - `_build_api_kwargs`
     - `_build_assistant_message`

2. **Tool execution loop helpers**
   - Nuevo módulo: `core/agent_runtime/tool_execution.py`
   - Extraído desde `run_agent.py`:
     - `_execute_tool_calls`
     - `_invoke_tool`
     - `_execute_tool_calls_concurrent`
     - `_execute_tool_calls_sequential`

`run_agent.py` mantiene la **fachada compatible** con wrappers 1:1 delegando a los módulos nuevos.

## Medición LOC (este corte)

- LOC antes de este corte (`run_agent.py`): **6063**
- LOC después de este corte (`run_agent.py`): **5125**
- Reducción en este corte: **938 LOC**

Acumulado T2 (desde baseline inicial 6250):
- 6250 → 5125 (**-1125 LOC**)

## Validación rápida (este corte)

Comandos ejecutados:

```bash
pytest -q -o addopts='' tests/test_agent_runtime_refactor_t2.py
python3 -m py_compile run_agent.py core/agent_runtime/runtime_context.py core/agent_runtime/conversation_utils.py core/agent_runtime/api_client_helpers.py core/agent_runtime/tool_execution.py
```

Resultado:
- `tests/test_agent_runtime_refactor_t2.py`: **5 passed**
- `py_compile`: **ok**

## Riesgos abiertos para siguiente corte T2

1. **Dependencias de entorno**: parte del stack real (por ejemplo `firecrawl`) no está instalado localmente; por eso la validación se mantiene focalizada y no full-suite.
2. **Fachada aún extensa**: pese al recorte fuerte, `run_agent.py` sigue grande; queda extraer más flujo del loop principal.
3. **Cobertura integrada**: los tests añadidos son mínimos y de regresión estructural; conviene ampliar tests end-to-end del bucle agente+tools.
