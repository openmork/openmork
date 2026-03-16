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

## Riesgos abiertos para siguiente corte T2

1. **Dependencias de test environment**: el suite completo de `run_agent` depende de paquetes no instalados en este entorno (`openai`, `dotenv`, `firecrawl`). Conviene normalizar entorno CI/local para validar regresión total.
2. **Fachada aún grande**: `AIAgent` sigue concentrando mucha lógica; el siguiente corte debe extraer bloques internos adicionales (cliente API, ejecución de tools, ciclo principal) en módulos dedicados.
3. **Cobertura focalizada**: se añadieron tests mínimos de regresión para este corte; falta ampliar cobertura integrada para garantizar equivalencia de comportamiento en flujos completos.
