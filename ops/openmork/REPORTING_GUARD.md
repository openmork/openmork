# Reporting Guard (anti-silencio, bajo consumo)

Objetivo: evitar que una tarea larga se quede sin reportes al usuario.

## Filosofía
- Bajo coste: no genera resúmenes largos ni bucles de mensajes.
- Solo alerta si hay silencio real.
- Cooldown anti-spam para no quemar tokens.

## Uso

```bash
# iniciar tarea (TTL por defecto 12 min)
python3 scripts/ops/reporting_guard.py start task-openmork-p0 --ttl-min 12

# marcar progreso (cada vez que haya avance)
python3 scripts/ops/reporting_guard.py progress task-openmork-p0 --note "preflight ok"

# cerrar tarea
python3 scripts/ops/reporting_guard.py done task-openmork-p0

# chequeo periódico (cron/systemd timer cada 5-10 min)
python3 scripts/ops/reporting_guard.py check --ttl-min 12 --cooldown-min 30
```

Salida esperada:
- `GUARD_OK no_overdue_tasks`
- `GUARD_ALERT overdue_tasks task-openmork-p0:18m`

## Recomendación producción
- Ejecutar `check` cada 10 min.
- TTL 12-15 min.
- Cooldown 30 min.

Así, si hay silencio, llega un aviso único y no se repite en bucle.
