# ROADMAP 48H — Openmork MVP status

Fecha: 2026-03-16

## 1) `/status` nativo de sesión
**Estado:** done (MVP)
- `/status` ahora muestra: model, tokens, contexto aprox (`last_prompt_tokens`), coste aprox, cola aprox y estado watchdog.
- Coste es estimación rough (fijo por token) para no depender de pricing por proveedor en esta tanda.

## 2) Políticas por herramienta por entorno (DEV/PROD)
**Estado:** done (MVP)
- Soporte `allow|ask|deny` por entorno con variables:
  - `OPENMORK_ENV` (ej. `dev`, `prod`)
  - `OPENMORK_TOOL_POLICY_<ENV>` (ej. `OPENMORK_TOOL_POLICY_DEV=ask`, `OPENMORK_TOOL_POLICY_PROD=deny`)
  - `OPENMORK_TOOL_POLICY_DEFAULT`
- En `deny`, comandos peligrosos quedan bloqueados por política.

## 3) Cron + recordatorios first-class
**Estado:** done (MVP)
- Nuevo comando `/remind`:
  - `/remind in:30m texto`
  - `/remind at:2026-03-16T18:00 texto`
- Crea jobs one-shot en cron con entrega al chat actual.

## 4) Canal announce unificado configurable por dominio/categoría
**Estado:** done (MVP)
- Nuevo router `gateway/announce.py` con resolución:
  1. `routes.domain.<domain>`
  2. `routes.category.<category>`
  3. `routes.default`
  4. fallback al home channel de plataforma
- Ejemplo en `ops/openmork/announce_routing.example.yaml`.

## 5) Watchdog + autohealing (caídas + 401/429)
**Estado:** partial
- Nuevo `gateway/watchdog.py`:
  - ventana temporal configurable
  - triggers por repetición 401/429
  - recomendación de acción (`reauth_required` / `rate_limit_backoff`)
- Integrado con gateway para contar errores detectados en respuestas/resultados del agente.
- Backlog: reinicio/recovery automático de adapters y remediación activa de caídas del gateway.

## Smoke tests añadidos
- `tests/gateway/test_status_command_mvp.py`
- `tests/tools/test_policy_env.py`
- `tests/gateway/test_announce_routing.py`
- `tests/gateway/test_watchdog_mvp.py`

## Backlog explícito (post-MVP)
- Coste real por proveedor/modelo (pricing table/versionado).
- Announce dispatch end-to-end (no solo resolución de target).
- Watchdog de disponibilidad de adapters + restart granular.
- Persistir métricas watchdog para observabilidad histórica.
