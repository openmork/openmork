# T12 — Gate final de calidad (go/no-go)

Fecha: 2026-03-17

## Checks ejecutados

### Typing
- `python -m mypy`
- Resultado: ✅ PASS (4 archivos perímetro core)

### Unit tests nuevas del tramo
- `pytest -q -o addopts='' tests/test_error_taxonomy.py tests/test_openmork_contracts.py tests/test_arm_registry.py`
- Resultado: ✅ PASS (`11 passed`)

### Gate global (repo completo)
- `python scripts/ops/check_except_pass.py --strict`
- Resultado: ❌ FAIL (baseline con 150 hallazgos fuera de perímetro de este tramo)

- `pytest tests/ -q --ignore=tests/integration --tb=short -n auto`
- Resultado: ❌ FAIL (`373 failed, 2029 passed, 165 errors`) por baseline y dependencias faltantes del entorno local

## Decisión

**NO-GO** para declarar calidad global del repo en este estado de entorno/baseline.

## Razones de no-go

1. Gate global de `except-pass` aún rojo en múltiples áreas históricas.
2. Test suite completa no está verde en entorno local actual.
3. Hay errores de import/dependencias en paquetes no relacionados con T6/T10.

## Riesgo residual

- Bajo en perímetro tocado (core runtime tipado + observabilidad) por tests y mypy en verde.
- Medio/alto para release global sin estabilizar baseline histórica.

## Recomendación inmediata

1. Encapsular gate global por perímetro (core/cli) mientras se quema deuda histórica.
2. Crear ola dedicada para limpiar `except-pass` legacy.
3. Restaurar entorno determinista de dependencias para suite completa.
