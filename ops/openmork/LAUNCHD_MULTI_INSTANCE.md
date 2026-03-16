# Openmork multi-instancia en macOS (launchd)

`systemd` no aplica en macOS. Para múltiples instancias, crea un plist por instancia y usa los scripts scoped de `scripts/ops/instance/`.

## Estructura sugerida

- Env por instancia: `/usr/local/etc/openmork/instances/<name>.env`
- Plists: `~/Library/LaunchAgents/com.openmork.<name>.plist`

## plist mínimo (por instancia)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.openmork.dev-a</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/opt/openmork/openmork/scripts/ops/instance/start_instance.sh</string>
    <string>/usr/local/etc/openmork/instances/dev-a.env</string>
  </array>

  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>WorkingDirectory</key><string>/opt/openmork/openmork</string>

  <key>StandardOutPath</key><string>/opt/openmork/instances/dev-a/log/launchd.out.log</string>
  <key>StandardErrorPath</key><string>/opt/openmork/instances/dev-a/log/launchd.err.log</string>
</dict>
</plist>
```

## Comandos

```bash
launchctl load ~/Library/LaunchAgents/com.openmork.dev-a.plist
launchctl unload ~/Library/LaunchAgents/com.openmork.dev-a.plist
launchctl kickstart -k gui/$(id -u)/com.openmork.dev-a
```

Para restart scoped usa:

```bash
scripts/ops/instance/restart_instance.sh /usr/local/etc/openmork/instances/dev-a.env
```
