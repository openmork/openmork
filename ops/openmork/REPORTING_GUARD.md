# Reporting Guard (anti-silencio, bajo consumo)

Objetivo: evitar silencio operativo sin generar spam ni gasto inútil de tokens.

## Qué hace ahora (auto + manual)

### 1) Flujo automático (event-driven)
En gateway, el guard se activa **solo** cuando detecta tarea potencialmente larga:
- prompt con intención de larga duración (ej: background/subagent/job/timeout), o
- hitos de tools típicas de tarea larga (ej: delegate_task, cronjob, terminal con timeout alto / comandos largos).

Ciclo automático:
1. `start(task_id)` al entrar en modo tarea larga.
2. `progress(task_id, note=...)` en hitos relevantes (sin spam).
3. `done(task_id)` al terminar (éxito o error).

`task_id` usado por gateway:
- sesión normal: `gw:<session_id>`
- `/background`: usa el `task_id` de background (`bg_HHMMSS_xxx`)

### 2) Override manual (MVP)
Comandos disponibles en gateway:

```text
/taskguard on <task_id>
/taskguard off <task_id>
/taskguard status <task_id>
```

- `on`: habilita override manual y arranca tracking para ese task_id.
- `off`: deshabilita override manual y marca tarea como done.
- `status`: devuelve estado compacto (running/done/idle, manual on/off, ttl).

## CLI script (ops)

```bash
# iniciar tarea (TTL por defecto 12 min)
python3 scripts/ops/reporting_guard.py start task-openmork-p0 --ttl-min 12

# marcar progreso
python3 scripts/ops/reporting_guard.py progress task-openmork-p0 --note "preflight ok"

# cerrar tarea
python3 scripts/ops/reporting_guard.py done task-openmork-p0

# chequeo periódico (cron/systemd timer cada 5-10 min)
python3 scripts/ops/reporting_guard.py check --ttl-min 12 --cooldown-min 30
```

Salida esperada:
- `GUARD_OK no_overdue_tasks`
- `GUARD_ALERT overdue_tasks task-openmork-p0:18m`

## Anti-spam / coste
- Mensajes compactos.
- Cooldown de alertas: **30 min** por tarea (por defecto).
- No hay bucles de alerta repetida mientras el cooldown esté activo.

## Mini guía real (producción)

1. Mantén `check` en cron cada 10 min.
2. TTL recomendado: 12-15 min para operaciones normales.
3. Si lanzas algo sensible/largo manualmente, activa:
   - `/taskguard on mi-task-prod-001`
4. Durante ejecución:
   - deja que auto `progress` haga el trabajo.
5. Al terminar o abortar:
   - `/taskguard off mi-task-prod-001` (si fue manual)

Resultado: cobertura anti-silencio, sin ruido y sin loops de avisos.
