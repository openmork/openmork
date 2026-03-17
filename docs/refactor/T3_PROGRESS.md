# T3 Progress — Split inicial de `cli.py` + arranque T4

Fecha: 2026-03-16

## Alcance T3 completado en este corte

1. **Split parse/dispatch en `cli.py` (manteniendo compatibilidad)**
   - Se separó la lógica en helpers explícitos:
     - `_resolve_toolsets_input(...)`
     - `_build_cli_from_main_args(...)`
     - `_dispatch_cli_mode(...)`
   - `main(...)` conserva firma/flags y comportamiento (gateway, worktree, list, query, interactive).

2. **Compatibilidad de comandos actual preservada**
   - No se cambiaron flags públicos ni orden de resolución de argumentos.
   - `fire.Fire(main)` sigue intacto.

3. **Tests smoke básicos de CLI añadidos**
   - Nuevo: `tests/test_cli_smoke_t3.py`
   - Cubre rutas mínimas:
     - parse toolsets string/default
     - dispatch list-tools (exit)
     - dispatch query quiet
     - dispatch interactive run

## Inicio T4 (MVP en este run)

1. **Primeros bloques `except ...: pass` eliminados donde era seguro**
   - `cli.py`
     - init opcional de skin: ahora `logger.warning(...)`
     - cleanup de terminal/browser/MCP: ahora log explícito
     - `_git_repo_root`: ahora `logger.debug(...)`
   - `core/agent_runtime/tool_execution.py`
     - checkpoint pre-save (concurrent + sequential): ahora `logger.warning(...)`
   - `core/agent_runtime/api_client_helpers.py`
     - cleanup en interrupción (API normal + streaming): ahora `logger.warning(...)`
     - callback de stream: ahora `logger.debug(...)`

2. **Regla/check para detectar `except-pass`**
   - Nuevo script: `scripts/ops/check_except_pass.py`
   - Nuevo test: `tests/test_except_pass_check.py`
   - Modo `--strict` devuelve exit code 1 si hay hallazgos.

## Medición LOC / impacto en `cli.py`

- LOC antes (`HEAD:cli.py`): **6024**
- LOC después (`working tree: cli.py`): **6050**
- Delta neto: **+26 LOC**

Nota: aunque sube LOC total, se mejora separación de responsabilidades en entrypoint (parse/build/dispatch).

## Validación ejecutada

```bash
python3 -m py_compile cli.py core/agent_runtime/tool_execution.py core/agent_runtime/api_client_helpers.py scripts/ops/check_except_pass.py
pytest -q -o addopts='' tests/test_cli_smoke_t3.py tests/test_except_pass_check.py
```

Resultado:
- `py_compile`: **ok**
- tests: **5 passed**

## Estado plan

- `ops/openmork/STATE_REFACTOR.yaml`
  - `T3`: **done**
  - `T4`: **in_progress**

## T4 pendiente tras este corte

- Estado actualizado (2026-03-17): el check anti-regresión se amplió a alcance repo (excluyendo `tests/`, `docs/`, `optional-skills/`, `reports/`) y actualmente no detecta `except Exception: pass` en superficie productiva.
- Siguiente paso recomendado: mantener vigilancia en PRs y exigir manejo explícito + logging semántico en nuevos bloques `except`.
