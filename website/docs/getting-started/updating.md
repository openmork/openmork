---
sidebar_position: 3
title: "Updating & Uninstalling"
description: "How to update OpenMork to the latest version or uninstall it"
---

# Updating & Uninstalling

## Updating

Update to the latest version with a single command:

```bash
openmork update
```

This pulls the latest code, updates dependencies, and prompts you to configure any new options that were added since your last update.

:::tip
`openmork update` automatically detects new configuration options and prompts you to add them. If you skipped that prompt, you can manually run `openmork config check` to see missing options, then `openmork config migrate` to interactively add them.
:::

### Updating from Messaging Platforms

You can also update directly from Telegram, Discord, Slack, or WhatsApp by sending:

```
/update
```

This pulls the latest code, updates dependencies, and restarts the gateway.

### Manual Update

If you installed manually (not via the quick installer):

```bash
cd /path/to/OpenMork
export VIRTUAL_ENV="$(pwd)/venv"

# Pull latest code and submodules
git pull origin main
git submodule update --init --recursive

# Reinstall (picks up new dependencies)
uv pip install -e ".[all]"
uv pip install -e "./mini-swe-agent"
uv pip install -e "./tinker-atropos"

# Check for new config options
openmork config check
openmork config migrate   # Interactively add any missing options
```

---

## Uninstalling

```bash
openmork uninstall
```

The uninstaller gives you the option to keep your configuration files (`~/.openmork/`) for a future reinstall.

### Manual Uninstall

```bash
rm -f ~/.local/bin/openmork
rm -rf /path/to/OpenMork
rm -rf ~/.openmork            # Optional — keep if you plan to reinstall
```

:::info
If you installed the gateway as a system service, stop and disable it first:
```bash
openmork gateway stop
# Linux: systemctl --user disable openmork-gateway
# macOS: launchctl remove ai.openmork.gateway
```
:::
