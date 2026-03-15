# De-Hermes NoTrace Audit (Sprint Final)

| File | Exact Reference | Category | Risk | Action |
|------|-----------------|----------|------|--------|
| `website/static/img/docs/cli-layout.svg` | Título "Hermes CLI / HERMES AGENT" | docs | low | replace |
| `website/static/img/docs/session-recap.svg` | Texto de ejemplo "Hermes" | docs | low | replace |
| `datagen-config-examples/example_browser_tasks.jsonl` | "Hermes" (mitológico) | historical | low | keep-temporary |
| `scripts/install.ps1` | `HERMES_HOME`, `.hermes`, `hermes.cmd` | installer-compat | medium | keep-temporary |
| `scripts/install.cmd` | urls y wrappers compat | installer-compat | low | keep-temporary |
| `scripts/dehermes/*` | Variables del script de score | historical | low | keep-temporary |
| `docs/architecture/DEHERMES_*` | Documentación del proceso | historical | low | keep-temporary |
