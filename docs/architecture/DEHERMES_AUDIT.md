# De-Hermes Audit (baseline + quick wins)

Fecha: 2026-03-15

## Alcance revisado
- `pyproject.toml`
- `uv.lock`
- imports Python
- docs (`docs/`, `README.md`, `website/`)
- scripts (`scripts/`)
- CI (`.github/workflows`)

## Resumen ejecutivo
- `pyproject.toml`: **sin acoples Hermes** detectados.
- `uv.lock`: quedó desacoplado de `hermes-agent` en el paquete raíz editable (quick win aplicado).
- Imports Python de runtime: **sin imports activos `hermes_*`** (solo string patterns en el nuevo script de scoring).
- Docs: persisten referencias en assets SVG del website (branding legacy, bajo riesgo técnico).
- Scripts: persiste acoplamiento alto en instaladores Windows (`scripts/install.ps1`, `scripts/install.cmd`) por rutas, variables y comandos `hermes`.
- CI: **sin referencias Hermes**.

## Inventario de acoples

| Área | Archivo | Acople detectado | Criticidad | Esfuerzo reemplazo |
|---|---|---|---|---|
| Scripts | `scripts/install.ps1` | `hermes-agent` repo URL, `HERMES_HOME`, `~/.hermes`, comando `hermes`, textos y paths legacy | Alta | Medio-Alto |
| Scripts | `scripts/install.cmd` | Wrapper con URLs `hermes-agent` y branding Hermes | Alta | Bajo-Medio |
| Docs web | `website/static/img/docs/cli-layout.svg` | Título/contenido textual “Hermes CLI / HERMES AGENT” | Baja | Bajo |
| Docs web | `website/static/img/docs/session-recap.svg` | Texto de ejemplo con “Hermes” | Baja | Bajo |
| Datagen ejemplo | `datagen-config-examples/example_browser_tasks.jsonl` | Prompt menciona “Hermes” (mitológico, no técnico) | Baja | Bajo |

## Quick wins aplicados en esta tanda
1. `uv.lock`: renombrado paquete editable raíz de `hermes-agent` a `openmork` (incluye `requires-dist` de extra `all`).
2. `scripts/security/check_dependency_integrity.py`: `ALLOWED_EDITABLE` reducido a `{"openmork"}`.
3. `package-lock.json` raíz: nombre del paquete actualizado a `openmork`.
4. `scripts/whatsapp-bridge/package-lock.json`: nombre actualizado a `openmork-whatsapp-bridge`.
5. `README.md`: referencia final actualizada a `OpenMork`.

## Riesgos y estabilidad
- **No se tocó** la lógica de runtime ni los flujos críticos del agente.
- Se pospone refactor completo de instaladores Windows para Fase 2 (compat layer) para evitar romper onboarding existente en sistemas que todavía esperan `hermes`.

## Decisiones de posposición (justificadas)
- Migrar `scripts/install.ps1`/`install.cmd` a `openmork` puro sin compat: **pospuesto**. Requiere capa de compatibilidad (alias/comando, rutas migrables y fallback) para evitar roturas de instalaciones previas.
