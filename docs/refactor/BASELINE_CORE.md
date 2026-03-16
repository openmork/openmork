# BASELINE_CORE — T1 Refactor Baseline (Openmork)

Fecha: 2026-03-16 (UTC)

## 1) Métricas base verificables (core/cli)

### LOC actuales
- `run_agent.py`: **6250** líneas
- `cli.py`: **6024** líneas

### Manejo de excepciones (patrones de riesgo)
- `run_agent.py`
  - `except Exception`: **60**
  - `except: pass`: **0**
- `cli.py`
  - `except Exception`: **86**
  - `except: pass`: **0**
- Total core/cli:
  - `except Exception`: **146**
  - `except: pass`: **0**

Comando usado para medir LOC y excepciones:
```bash
python3 - <<'PY'
from pathlib import Path
import re
root=Path('.')
files=[root/'run_agent.py', root/'cli.py']
for f in files:
    text=f.read_text(encoding='utf-8', errors='ignore')
    loc=sum(1 for _ in f.open('r', encoding='utf-8', errors='ignore'))
    exc_exception=len(re.findall(r'^\s*except\s+Exception\b', text, flags=re.M))
    exc_pass=len(re.findall(r'^\s*except\s*:\s*\n\s*pass\b|^\s*except\s*:\s*pass\b', text, flags=re.M))
    print(f"{f.name}|loc={loc}|except_exception={exc_exception}|except_pass={exc_pass}")
PY
```

Salida:
```text
run_agent.py|loc=6250|except_exception=60|except_pass=0
cli.py|loc=6024|except_exception=86|except_pass=0
```

## 2) Estado de tests críticos disponibles

Comando intentado (inicial):
```bash
pytest -q tests/test_run_agent_codex_responses.py tests/tools/test_tirith_security.py
```
Resultado: **FAIL en arranque de pytest** por `-n` inyectado en `addopts` sin plugin compatible en runtime actual.

Comando alternativo ejecutado (sin addopts global):
```bash
pytest -q -o addopts='' tests/test_run_agent_codex_responses.py tests/tools/test_tirith_security.py
```
Resultado: **FAIL en colección** por dependencia faltante:
- `ModuleNotFoundError: No module named 'openai'`

Conclusión de baseline test:
- Suite crítica seleccionada existe, pero **no ejecutable en este runtime actual** sin ajustar entorno de dependencias/pytest.

## 3) Preflight T1 (refactor)

Script implementado:
- `scripts/ops/refactor_preflight.py`

Salida JSON:
- `reports/refactor_preflight_status.json`

Comando exacto ejecutado:
```bash
python3 scripts/ops/refactor_preflight.py; echo EXIT_CODE:$?
```

Resumen del resultado:
- Estado global: **FAIL**
- Exit code: **1**
- Checks:
  - `auth_runtime`: **FAIL** (`api_key` ausente)
  - `basic_deps`: **OK**
  - `safety_flags`: **OK**
  - `web_connectivity`: **OK**
  - `repo_sanity`: **OK**

## 4) Riesgos inmediatos detectados

1. **Bloqueo de runtime auth**: no hay API key activa para provider/model configurado → impide validaciones de flujo real contra proveedor.
2. **Tests críticos no ejecutables en entorno actual**: falta módulo `openai`; adicionalmente la configuración de pytest depende de `-n` (xdist) no disponible en este runtime.
3. **Superficie alta de `except Exception` (146 total)** en archivos core/cli → riesgo de enmascarar errores durante refactor si no se acota por tipos de excepción.

## 5) Estado T1

- Baseline técnico creado y trazable.
- Preflight específico de refactor creado, ejecutado y evidenciado.
- T1 listo para cierre administrativo en `STATE_REFACTOR.yaml`.
