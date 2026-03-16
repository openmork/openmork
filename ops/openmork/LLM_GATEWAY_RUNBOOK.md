# LLM Gateway Runbook (DEV)

## Activar en DEV
1. Copiar ejemplo y adaptar en ruta segura fuera del repo (recomendado):
   - `cp ops/openmork/llm_gateway.example.yaml ~/.openmork/llm_gateway.yaml`
2. Definir flags/env:
   - `OPENMORK_LLM_GATEWAY_ENABLED=true`
   - `OPENMORK_LLM_GATEWAY_CONFIG=~/.openmork/llm_gateway.yaml`
3. Asegurar que las `api_key_env` referenciadas existan en `~/.openmork/.env` o entorno.

## Smoke test rápido
1. Levantar flujo normal (chat/gateway) en DEV.
2. Verificar que runtime incluya:
   - `source=llm-gateway:<route_id>`
   - `gateway_route_id` presente.
3. Verificar sticky:
   - dos requests con mismo `conversation_id` mantienen `route_id`.

## Validación de salud
- Simular `429` con `report_gateway_route_result(route_id, 429)`:
  - la ruta entra en cooldown y rota a otra saludable.
- Simular `401`/`403`:
  - la ruta entra en cuarentena y queda fuera del pool.
- Esperar expiración y confirmar recuperación automática.

## Rollback rápido
- Desactivar toggle:
  - `OPENMORK_LLM_GATEWAY_ENABLED=false` (o unset)
- Mantener/retirar `OPENMORK_LLM_GATEWAY_CONFIG` según necesidad.
- Reiniciar proceso de Openmork (CLI/gateway service).
- Resultado esperado: vuelve el flujo legacy de `runtime_provider` sin gateway.

## Seguridad
- No almacenar secretos en repo.
- Preferir `api_key_env`.
- Limitar uso a DEV hasta completar observabilidad y controles operativos ampliados.
