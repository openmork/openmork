# No-Trace Audit (strict mode)

Fecha: 2026-03-16

## Estado
- Guard de no-trace en tolerancia 0.
- Sin allowlist activa.
- Cualquier aparición legacy fuera de exclusiones técnicas (binarios/dependencias externas) falla en CI.

## Validación
Ejecutar:
- `python3 scripts/dehermes/no_trace_guard.py`
- `python3 scripts/security/check_secrets.py --all-files`
- `python3 scripts/security/check_dependency_integrity.py --lock uv.lock`
