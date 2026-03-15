# OpenMork — ACP (Agent Client Protocol) Setup Guide

OpenMork supports the **Agent Client Protocol (ACP)**, allowing it to run as
a coding agent inside your editor. ACP lets your IDE send tasks to OPENMORK, and
OPENMORK responds with file edits, terminal commands, and explanations — all shown
natively in the editor UI.

---

## Prerequisites

- OpenMork installed and configured (`openmork setup` completed)
- An API key / provider set up in `~/.openmork/.env` or via `openmork login`
- Python 3.11+

Install the ACP extra:

```bash
pip install -e ".[acp]"
```

---

## VS Code Setup

### 1. Install the ACP Client extension

Open VS Code and install **ACP Client** from the marketplace:

- Press `Ctrl+Shift+X` (or `Cmd+Shift+X` on macOS)
- Search for **"ACP Client"**
- Click **Install**

Or install from the command line:

```bash
code --install-extension anysphere.acp-client
```

### 2. Configure settings.json

Open your VS Code settings (`Ctrl+,` → click the `{}` icon for JSON) and add:

```json
{
  "acpClient.agents": [
    {
      "name": "OpenMork",
      "registryDir": "/path/to/OpenMork/acp_registry"
    }
  ]
}
```

Replace `/path/to/OpenMork` with the actual path to your OpenMork
installation (e.g. `~/.openmork/OpenMork`).

Alternatively, if `openmork` is on your PATH, the ACP Client can discover it
automatically via the registry directory.

### 3. Restart VS Code

After configuring, restart VS Code. You should see **OpenMork** appear in
the ACP agent picker in the chat/agent panel.

---

## Zed Setup

Zed has built-in ACP support.

### 1. Configure Zed settings

Open Zed settings (`Cmd+,` on macOS or `Ctrl+,` on Linux) and add to your
`settings.json`:

```json
{
  "acp": {
    "agents": [
      {
        "name": "OpenMork",
        "registry_dir": "/path/to/OpenMork/acp_registry"
      }
    ]
  }
}
```

### 2. Restart Zed

OpenMork will appear in the agent panel. Select it and start a conversation.

---

## JetBrains Setup (IntelliJ, PyCharm, WebStorm, etc.)

### 1. Install the ACP plugin

- Open **Settings** → **Plugins** → **Marketplace**
- Search for **"ACP"** or **"Agent Client Protocol"**
- Install and restart the IDE

### 2. Configure the agent

- Open **Settings** → **Tools** → **ACP Agents**
- Click **+** to add a new agent
- Set the registry directory to your `acp_registry/` folder:
  `/path/to/OpenMork/acp_registry`
- Click **OK**

### 3. Use the agent

Open the ACP panel (usually in the right sidebar) and select **OpenMork**.

---

## What You Will See

Once connected, your editor provides a native interface to OpenMork:

### Chat Panel
A conversational interface where you can describe tasks, ask questions, and
give instructions. OPENMORK responds with explanations and actions.

### File Diffs
When OPENMORK edits files, you see standard diffs in the editor. You can:
- **Accept** individual changes
- **Reject** changes you don't want
- **Review** the full diff before applying

### Terminal Commands
When OPENMORK needs to run shell commands (builds, tests, installs), the editor
shows them in an integrated terminal. Depending on your settings:
- Commands may run automatically
- Or you may be prompted to **approve** each command

### Approval Flow
For potentially destructive operations, the editor will prompt you for
approval before OPENMORK proceeds. This includes:
- File deletions
- Shell commands
- Git operations

---

## Configuration

OpenMork under ACP uses the **same configuration** as the CLI:

- **API keys / providers**: `~/.openmork/.env`
- **Agent config**: `~/.openmork/config.yaml`
- **Skills**: `~/.openmork/skills/`
- **Sessions**: `~/.openmork/state.db`

You can run `openmork setup` to configure providers, or edit `~/.openmork/.env`
directly.

### Changing the model

Edit `~/.openmork/config.yaml`:

```yaml
model: openrouter/nous/openmork-3-llama-3.1-70b
```

Or set the `OPENMORK_MODEL` environment variable.

### Toolsets

ACP sessions use the curated `openmork-acp` toolset by default. It is designed for editor workflows and intentionally excludes things like messaging delivery, cronjob management, and audio-first UX features.

---

## Troubleshooting

### Agent doesn't appear in the editor

1. **Check the registry path** — make sure the `acp_registry/` directory path
   in your editor settings is correct and contains `agent.json`.
2. **Check `openmork` is on PATH** — run `which openmork` in a terminal. If not
   found, you may need to activate your virtualenv or add it to PATH.
3. **Restart the editor** after changing settings.

### Agent starts but errors immediately

1. Run `openmork doctor` to check your configuration.
2. Check that you have a valid API key: `openmork status`
3. Try running `openmork acp` directly in a terminal to see error output.

### "Module not found" errors

Make sure you installed the ACP extra:

```bash
pip install -e ".[acp]"
```

### Slow responses

- ACP streams responses, so you should see incremental output. If the agent
  appears stuck, check your network connection and API provider status.
- Some providers have rate limits. Try switching to a different model/provider.

### Permission denied for terminal commands

If the editor blocks terminal commands, check your ACP Client extension
settings for auto-approval or manual-approval preferences.

### Logs

OPENMORK logs are written to stderr when running in ACP mode. Check:
- VS Code: **Output** panel → select **ACP Client** or **OpenMork**
- Zed: **View** → **Toggle Terminal** and check the process output
- JetBrains: **Event Log** or the ACP tool window

You can also enable verbose logging:

```bash
OPENMORK_LOG_LEVEL=DEBUG openmork acp
```

---

## Further Reading

- [ACP Specification](https://github.com/anysphere/acp)
- [OpenMork Documentation](https://github.com/openmork/OpenMork)
- Run `openmork --help` for all CLI options
