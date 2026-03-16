# De-Hermes NoTrace Audit (Sprint Final — Fase 1)

Estado recalculado con `python3 scripts/dehermes/score.py`.

## Residuales exactos actuales

Tras limpiar installers y guard, **solo quedan referencias legacy en este mismo documento** (contexto histórico/auditoría):

| File | Exact reference | Count | Category | Motivo | Acción |
|------|------------------|-------|----------|--------|--------|
| `docs/architecture/DEHERMES_NOTRACE_AUDIT.md` | `Hermes` / `HERMES` (texto explicativo) | 4 | docs | Registro explícito del término legacy auditado | mantener temporalmente |
| `docs/architecture/DEHERMES_NOTRACE_AUDIT.md` | `HERMES_HOME` | 1 | docs | Evidencia de variable legacy mencionada en auditoría | mantener temporalmente |
| `docs/architecture/DEHERMES_NOTRACE_AUDIT.md` | `.hermes` | 1 | docs | Evidencia de path legacy mencionada en auditoría | mantener temporalmente |

## Excepciones allowlist (`scripts/dehermes/no_trace_guard.py`)

Excepciones mínimas activas y justificadas:

- `scripts/dehermes/score.py` → contiene patrones de medición legacy necesarios para calcular score.
- `reports/dehermes_score.json` → artefacto histórico de score; puede incluir menciones previas.
- `docs/architecture/DEHERMES_AUDIT.md` → historial del proceso de migración.
- `docs/architecture/DEHERMES_ROADMAP.md` → roadmap de eliminación legacy.
- `docs/architecture/DEHERMES_NOTRACE_AUDIT.md` → este reporte de residuales exactos.
- `ops/openmork/GEMINI_NOTRACE_SPRINT.md` → bitácora del sprint de limpieza.
- `datagen-config-examples/example_browser_tasks.jsonl` → referencia mitológica histórica (no branding de producto).
