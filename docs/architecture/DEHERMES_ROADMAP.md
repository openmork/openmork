# De-Hermes Roadmap (48–72h ejecutable)

Fecha: 2026-03-15

Objetivo: reducir dependencia estructural de Hermes y dejar OpenMork soberano sin romper flujos actuales.

## Fase 1 — Desacople fácil (nombres, dependencias editables, tooling)

### Trabajo
- Normalizar naming residual (`hermes-agent` -> `openmork`) en lock/config seguros.
- Alinear checks de integridad para permitir solo editable `openmork`.
- Añadir métrica automática de independencia (score baseline + reporte JSON).
- Limpiar referencias triviales de docs generales y package metadata.

### Criterios de salida (medibles)
- [x] `pyproject.toml` sin `hermes-agent`.
- [x] `uv.lock` paquete editable raíz en `openmork`.
- [x] `scripts/security/check_dependency_integrity.py` permite solo `openmork`.
- [x] Script de scoring disponible en `scripts/dehermes/score.py`.
- [x] Baseline generado en `reports/dehermes_score.json`.

## Fase 2 — Compat layer (sin romper legado)

### Trabajo
- Refactor controlado de instaladores Windows (`install.ps1`, `install.cmd`):
  - branding `openmork`
  - repo URLs `openmork`
  - comando principal `openmork` con alias de compat `hermes` (temporal)
  - migración de rutas `~/.hermes` -> `~/.openmork` con fallback y aviso
- Introducir constantes de compatibilidad centralizadas para evitar strings hardcoded.
- Agregar tests smoke para instalación/arranque en modo compat.

### Criterios de salida (medibles)
- [ ] 0 referencias hardcoded a `hermes-agent` en scripts de instalación.
- [ ] Comando `openmork` funcional en instalación limpia.
- [ ] Alias `hermes` mantiene backward compatibility durante transición.
- [ ] Test smoke de installer/entrypoint pasando en CI (o job dedicado).

## Fase 3 — Independencia core

### Política de retirada de compat legacy (`hermes`)
- **Objetivo de retirada**: OpenMork `v1.0.0` o, como máximo, `2026-06-30` (lo que ocurra primero).
- **Criterio de salida**: retirar alias `hermes` cuando se cumpla al menos una condición:
  - adopción de comando `openmork` >= **90%** en telemetría de instaladores/smoke logs durante 30 días, o
  - llegada de release mayor `v1.0.0` con nota de breaking change publicada.
- **Condición de seguridad**: mantener fallback documentado solo durante la ventana de transición; después, eliminar wrappers `hermes.*` del installer.

### Trabajo
- Eliminar alias y rutas legacy tras ventana de transición.
- Depurar assets/docs de branding Hermes en website y ejemplos.
- Consolidar contrato de configuración y rutas bajo namespace OpenMork.
- Subir umbral mínimo de score de independencia como guardrail CI.

### Criterios de salida (medibles)
- [ ] 0 referencias `hermes-agent` en repo (excepto changelog histórico explícito).
- [ ] 0 uso de `HERMES_HOME` / `~/.hermes` en runtime principal.
- [ ] Score de independencia >= 85 mantenido en CI.
- [ ] Documentación oficial 100% OpenMork.

## Riesgos clave y mitigación
- Riesgo: romper instalaciones existentes que esperan `hermes`.
  - Mitigación: capa compat temporal + migración no destructiva + smoke tests.
- Riesgo: lock/config drift.
  - Mitigación: regeneración lock controlada y check de integridad en CI.
- Riesgo: cambios de branding sin impacto funcional pero dispersos.
  - Mitigación: checklist por dominio (scripts/docs/website/config) con score tracking.
