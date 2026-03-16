# Openmork LLM Gateway (DEV) — MVP Spec

## Objetivo
Implementar un gateway interno para enrutar solicitudes LLM entre múltiples proveedores/credenciales con políticas legítimas de salud/coste/latencia, sin evasión de TOS.

## Arquitectura

### 1) Router
- Entrada: `conversation_id`, `requested_model`.
- Salida: ruta efectiva (`provider`, `base_url`, `api_key`, `route_id`, `api_mode`).
- Política principal: **weighted round-robin** entre rutas saludables compatibles con el modelo.

### 2) Credential Manager
- Carga pool desde YAML externo (`OPENMORK_LLM_GATEWAY_CONFIG`).
- Cada ruta define:
  - `id`
  - `provider`
  - `base_url`
  - `api_key_env` (preferido) o `api_key` literal (solo DEV temporal)
  - `models[]`
  - `weight`
  - `cost_tier`, `latency_tier`

### 3) Health Engine
- Estado por ruta:
  - `quarantined_until` (401/403)
  - `cooldown_until` (429)
  - `last_error`
- Se excluyen rutas no saludables de la selección.

### 4) Policy Engine
- **Rotación base:** weighted RR.
- **Desempate:** menor `cost_tier`, luego menor `latency_tier`, luego `route_id`.
- **Sticky por conversación:** se conserva ruta mientras esté saludable y compatible.
- **Fallback:** si sticky falla o queda no saludable, se reasigna al siguiente candidato saludable.

## Reglas de rotación

### 429 (rate limit)
- Acción: cooldown temporal.
- Estado: `cooldown_until = now + cooldown_seconds`.
- Efecto: ruta excluida hasta expirar cooldown.

### 401 / 403 (auth/forbidden)
- Acción: quarantine.
- Estado: `quarantined_until = now + quarantine_seconds`.
- Efecto: ruta excluida durante cuarentena (requiere intervención/rotación natural al expirar).

### Recuperación
- Al expirar ventanas (`cooldown`/`quarantine`), ruta vuelve automáticamente al pool si sigue teniendo credencial válida.

## Sticky por conversación
- Mapa en memoria `conversation_id -> route_id`.
- Si la ruta sticky está saludable + compatible, se reutiliza.
- Si no, se reemplaza por una nueva ruta saludable.

## Observabilidad mínima (MVP)
- `source = llm-gateway:<route_id>` inyectado en runtime.
- `gateway_route_id` y `gateway_sticky` devueltos para logs/diagnóstico.
- API explícita para reportar resultados HTTP y actualizar salud:
  - `report_gateway_route_result(route_id, status_code)`.

## Integración con Openmork runtime_provider
- `resolve_runtime_provider(...)` intenta primero resolver ruta del gateway (si está habilitado y configurado).
- Si gateway no está habilitado/configurado o no encuentra ruta válida, continúa el flujo existente intacto.

## Separación DEV/PROD
- Activación por flag y config explícita:
  - `OPENMORK_LLM_GATEWAY_ENABLED=true`
  - `OPENMORK_LLM_GATEWAY_CONFIG=/ruta/segura/llm_gateway.yaml`
- Sin flag/config: comportamiento legacy sin cambios.
