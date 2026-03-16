# Legacy Compatibility Removal Roadmap (completado)

Fecha: 2026-03-16

Objetivo: eliminar por completo restos de compatibilidad legacy en runtime, installers, CI y documentación operativa.

## Estado actual

- Compatibilidad legacy retirada en instaladores Windows.
- Variables de entorno legacy retiradas.
- Guard de rastreo endurecido a tolerancia 0.
- Referencias operativas legacy eliminadas en docs de arquitectura.

## Cambios cerrados

- `scripts/install.ps1`
  - eliminado shim de comando legacy.
  - eliminado alias de variable de entorno legacy.
- `scripts/install.cmd`
  - eliminada nota de compatibilidad temporal.
- `scripts/dehermes/no_trace_guard.py`
  - modo de tolerancia 0 sin allowlist activa.
- `docs/architecture/OPENMORK_V1_READY.md`
  - checklist alineado con estado sin compat legacy.

## Política de mantenimiento

- No se reintroducen shims legacy en runtime ni instaladores.
- Cualquier cambio upstream se integra mediante cherry-pick manual y revisión explícita antes de merge.

## Criterio de aceptación

- 0 referencias legacy en runtime/installers/CI/docs operativas.
- Guard de rastreo en verde en local y CI.
