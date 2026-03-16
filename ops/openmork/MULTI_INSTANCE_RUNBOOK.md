# Openmork Multi-Instance Runbook (DEV -> PROD)

Objetivo: operar múltiples instancias en el mismo host sin acciones globales ni interferencias cruzadas.

## Principios de seguridad

- Cada instancia tiene su propio `PID_FILE`, `LOG_FILE` y `INSTANCE_LOCK_FILE`.
- Los scripts usan solo el PID de su instancia (`kill <pid>`), nunca `pkill` global.
- El restart aplica lock por instancia para evitar carreras.

## 1) Crear una instancia (DEV)

1. Copia la plantilla:

```bash
cp ops/openmork/instance.env.example ops/openmork/dev-a.env
```

2. Ajusta variables **únicas** para la instancia:
- `INSTANCE_NAME`
- `OPENMORK_HOME`
- `OPENMORK_REPO`
- `OPENMORK_ENV_FILE`
- `PID_FILE`
- `LOG_FILE`
- `INSTANCE_LOCK_FILE`
- `MODEL`

3. Prepara estructura:

```bash
scripts/ops/instance/bootstrap_instance.sh ops/openmork/dev-a.env
```

## 2) Start / Stop / Restart scoped

```bash
scripts/ops/instance/start_instance.sh ops/openmork/dev-a.env
scripts/ops/instance/stop_instance.sh ops/openmork/dev-a.env
scripts/ops/instance/restart_instance.sh ops/openmork/dev-a.env
```

Comportamiento:
- `start`: no arranca de nuevo si el PID sigue vivo.
- `stop`: termina solo el PID de la instancia; limpia pid stale.
- `restart`: lock por instancia + stop + start.

## 3) Healthcheck

```bash
scripts/ops/instance/health_instance.sh ops/openmork/dev-a.env
```

- Check base: PID existe y proceso vivo.
- Check opcional: `HEALTH_URL` si está definido.

## 4) systemd en Linux (PROD)

1. Guarda envs en `/etc/openmork/instances/<instance>.env`.
2. Instala `ops/openmork/systemd/openmork@.service` en `/etc/systemd/system/`.
3. Recarga y habilita instancia:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openmork@dev-a
sudo systemctl status openmork@dev-a
```

## 5) macOS alternativa

Ver: `ops/openmork/LAUNCHD_MULTI_INSTANCE.md`

## Troubleshooting

- **"pid file not found"**: ejecutar `bootstrap_instance.sh` y revisar rutas.
- **"stale pid file"**: script limpia automático; validar que no haya colisión de `PID_FILE` entre instancias.
- **health URL falla pero PID vivo**: revisar endpoint y firewall local.
- **restart lock active**: hay otro restart en curso para la misma instancia; esperar o eliminar lock si quedó huérfano tras validar.

## Rollout recomendado

1. Validar en DEV con 2 instancias (`dev-a`, `dev-b`) en el mismo host.
2. Confirmar aislamiento de PID/logs por instancia.
3. Migrar a PROD con envs en `/etc/openmork/instances/`.
4. Activar servicios de forma incremental (una instancia a la vez).
