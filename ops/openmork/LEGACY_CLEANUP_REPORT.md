# LEGACY CLEANUP REPORT — openmork (DEV)

Fecha: 2026-03-17

## Resumen ejecutivo
Se ejecutó una limpieza adicional enfocada en:
1) referencias legacy no necesarias en superficie operativa,
2) reducción de `except Exception: pass`,
3) consolidación de ownership técnico de openmork.

## A) Barrido legacy

### Cambios aplicados
- `honcho_integration/cli.py`
  - Texto de migración normalizado para evitar framing legacy innecesario en mensajes de UX.
- `README.md`
  - Acknowledgements ajustados para dejar explícito que el mantenimiento actual es del equipo openmork.
- `pyproject.toml`
  - `authors` y `maintainers` establecidos como `openmork core maintainers`.
  - URLs del proyecto apuntando a `https://github.com/openmork/openmork`.

### Métrica (legacy refs operativas)
Definición usada: ocurrencias `openclaw|OpenClaw` excluyendo superficies justificadas de compatibilidad/documentación comparativa:
- `docs/migration/**`
- `optional-skills/migration/**`
- `docs/honcho-integration-spec.*`
- `scripts/dehermes/**`

- **Antes:** 204
- **Después:** 200
- **Delta:** -4

### Residuales justificados
Se mantienen referencias legacy en zonas de compatibilidad/migración y documentación comparativa para no romper:
- flujos de migración OpenClaw → openmork,
- documentación técnica comparativa de integración Honcho,
- componentes explícitos de scoring/auditoría histórica.

## B) Campaña `except Exception: pass`

### Cambios aplicados (lote incremental)
Se reemplazaron bloques silenciosos por manejo explícito + logging en:
- `openmork_time.py`
- `openmork_cli/banner.py`
- `openmork_cli/clipboard.py`
- `openmork_cli/models.py`
- `openmork_cli/auth.py`

Además, se amplió el guard anti-regresión:
- `scripts/ops/check_except_pass.py`
  - alcance repo Python (excluyendo `tests/`, `docs/`, `optional-skills/`, `reports/`),
  - soporte de umbral en modo estricto con `--max-findings` (ratcheting progresivo).
- baseline inicial documentada en `ops/openmork/except_pass_baseline.txt`.

### Métrica (`except-pass` en código productivo)
Medición con `scripts/ops/check_except_pass.py` (scope productivo del script):
- **Antes:** 160
- **Después:** 150
- **Delta:** -10

### Residuales justificados
Quedan 150 hallazgos en runtime histórico (principalmente `cli.py`, `gateway/run.py`, `run_agent.py` y módulos de integración). Se mantienen temporalmente por compatibilidad operativa; requieren barrido por lotes para no introducir regresiones de runtime.

## C) Ownership / branding técnico

- `pyproject.toml` actualizado para ownership de openmork.
- README actualizado para narrativa de mantenimiento propio.
- Mensajes UX en flujo Honcho des-legacy donde no era necesario.

## D) Tests/validación ejecutados

```bash
python3 -m py_compile scripts/ops/check_except_pass.py openmork_time.py openmork_cli/banner.py openmork_cli/clipboard.py openmork_cli/models.py openmork_cli/auth.py honcho_integration/cli.py
pytest -q -o addopts='' tests/test_except_pass_check.py
```

Resultado:
- `py_compile`: OK
- `pytest`: 2 passed

## E) Commits propuestos (push-ready)
1. `chore(openmork): tighten ownership metadata and remove unnecessary legacy wording`
2. `refactor(runtime): replace silent except-pass batch with explicit debug logging`
3. `chore(ops): expand except-pass guard with thresholded strict mode and cleanup report`
