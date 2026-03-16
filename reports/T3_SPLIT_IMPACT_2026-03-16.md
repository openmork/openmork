# T3 split impact (parse/dispatch)

Date: 2026-03-16

## Current structure

- `openmork_cli/main.py`: command wiring + parser/dispatch entrypoints
- `openmork_cli/commands.py`: centralized slash command registry + completer
- `cli.py`: legacy interactive runtime (still large, but decoupled from CLI command registry)

## LOC snapshot

- `cli.py`: 6050 LOC
- `openmork_cli/main.py`: 3412 LOC
- `openmork_cli/commands.py`: 122 LOC

## Compatibility status

- Command registry remains backward-compatible via `COMMANDS` flat dict.
- Parse/dispatch route remains through `openmork_cli.main:main` entrypoint.
- Existing update command tests continue passing (`tests/openmork_cli/test_cmd_update.py`).

## Note

T3 split base is complete and stable; remaining structural debt is mostly in legacy `cli.py` runtime, not parser/dispatch command definitions.
