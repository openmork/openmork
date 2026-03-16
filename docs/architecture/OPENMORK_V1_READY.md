# OPENMORK v1 Readiness (Production-Grade Polish)

## Estado actual real

OpenMork v1 queda endurecido para operación estable con:

- Contratos ARM (`gateway`, `memory`, `security`, `skillset`) validados en runtime.
- Registro central (`openmork_arm_registry`) integrado en flujo real:
  - `gateway`: registro en `gateway/run.py`
  - `memory`, `security`, `skillset`: registro en `run_agent.py`
- Diagnóstico de estado ARM disponible por CLI:
  - `openmork status --arms`
- Métricas por arm persistidas automáticamente en:
  - `~/.openmork/reports/arm_registry_status.json`

## Qué está endurecido

- Compatibilidad legacy retirada en installers y guardrails (modo estricto).
- No se mantienen alias legacy de comando ni variables de entorno de transición.
- Los updates de upstream se integran por cherry-pick manual, con revisión antes de merge.

1. **Registry integration completa**
   - `security` y `skillset` ya no son solo contratos “pasivos”: se registran en runtime con metadata y healthcheck.
   - Security arm participa en validación real de `terminal.command` en `tools/terminal_tool.py`.

2. **Observabilidad útil**
   - Métricas mínimas por arm: `count`, `error`, `latency_ms_avg`, `latency_ms_total`.
   - Persistencia best-effort a JSON para troubleshooting offline.
   - `openmork status --arms` muestra resumen operativo rápido.

3. **CI hardening**
   - Se mantienen guardrails de seguridad (`security-check.yml`).
   - Se añade smoke job rápido para contratos/registry en cada PR (`tests.yml`: `contracts-registry-smoke`).

## Checklist de arranque producción

- [ ] Configurar `.env` y `config.yaml` (proveedor/modelo/credenciales mínimas)
- [ ] Ejecutar guardrails locales:
  - `python3 scripts/dehermes/no_trace_guard.py`
  - `python3 scripts/security/check_secrets.py --all-files`
  - `python3 scripts/security/check_dependency_integrity.py --lock uv.lock`
- [ ] Ejecutar tests críticos:
  - `pytest -q -o addopts='' tests/test_openmork_contracts.py tests/test_arm_registry.py`
- [ ] Verificar diagnóstico ARM:
  - `openmork status --arms`
- [ ] Confirmar que existe y se actualiza:
  - `~/.openmork/reports/arm_registry_status.json`

## Dónde mirar cuando algo falla

1. **Diagnóstico rápido ARM**
   - `openmork status --arms`
2. **Dump persistido completo**
   - `~/.openmork/reports/arm_registry_status.json`
3. **Errores de guardias de seguridad/terminal**
   - revisar salida de tool `terminal` y logs de sesión
4. **Contratos rotos**
   - `tests/test_openmork_contracts.py`
   - `tests/test_arm_registry.py`

## Límites actuales conocidos

- La persistencia del registro ARM es best-effort (si no puede escribir archivo, no rompe runtime).
- Las métricas actuales son agregadas por proceso/archivo (no TSDB ni series temporales avanzadas).
- `status --arms` usa dump persistido; si no hubo actividad/runtime reciente, puede mostrar estado vacío o antiguo.

## Mitigación recomendada de límites

- Ejecutar `openmork status --arms` después de una sesión real para refrescar estado.
- Integrar exportador de métricas (Prometheus/OpenTelemetry) en fase siguiente sin romper compatibilidad actual.
