# T11 — Matriz de compatibilidad y migración controlada

## Matriz (CLI/Core)

| Componente | Estado | Compatibilidad | Nota |
|---|---|---|---|
| `run_agent.py` público | estable | ✅ backward compatible | Refactor en módulos `core/agent_runtime/*` sin romper API pública |
| `openmork` CLI entrypoint | estable | ✅ compatible | Sin cambios de flags destructivos |
| Tool calling (`tool_call_id`, payload) | estable | ✅ compatible | Solo se agrega observabilidad estructurada |
| Checkpoint pre-save | estable | ✅ compatible | Errores pasan a logging tipado, comportamiento conservado |
| Config de tests CI | extendido | ✅ compatible | Se añade type-check de perímetro, sin eliminar checks previos |

## Deprecations (controladas)

No se introducen deprecaciones runtime obligatorias en este tramo.

Se define política para próximos cortes:

1. anunciar en release N
2. warning no-blocking en N+1
3. retirada en N+2

## Migración recomendada (equipos)

1. actualizar a versión con `error_taxonomy`
2. conectar parser de logs a `code/severity/context`
3. activar gate de type-check en CI local para archivos de perímetro
4. validar smoke de herramientas críticas (`read/write/patch/terminal/process`)
