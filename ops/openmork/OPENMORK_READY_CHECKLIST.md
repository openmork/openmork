# OPENMORK READY CHECKLIST (P0)

Última actualización: 2026-03-16T05:56Z

## Checks P0

- [x] **Preflight bloqueante** (`scripts/ops/preflight_check.py`)
  - provider/model smoke prompt
  - web fetch básico
  - seguridad (`safety.yaml` + tirith)
  - pairing/home channel configurado
- [x] **Restart seguro + healthcheck** (`scripts/ops/restart_gateway_safe.sh`)
  - restart gateway
  - espera activa con timeout
  - validación proceso + ping bot
  - rollback si falla
  - log en `~/.openmork/openmork-restart.log`
- [x] **Reporte JSON de preflight**
  - `reports/preflight_status.json`

## Último estado

- Preflight: **FAIL**
- Restart healthcheck: **FAIL**
- Estado general P0: **FAIL (implementado, pendiente entorno)**

## Comando único para ver estado

```bash
python3 scripts/ops/preflight_check.py; echo $?; tail -n 80 ~/.openmork/openmork-restart.log
```
