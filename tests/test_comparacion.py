from mnemo.cognitivo.comparacion import comparar
from mnemo.cognitivo.simulacion import simular_eventos


def test_los_modelos_superan_a_la_linea_base():
    salida = comparar(simular_eventos(n_estudiantes=60, n_items=8, semilla=1))
    r = salida["resultados"]
    assert r["Base (tasa media de acierto)"]["auc"] == 0.5
    assert r["ACT-R (τ y s ajustados)"]["auc"] > 0.75
    assert r["Random Forest"]["auc"] > 0.75
    assert salida["actr"].ruido > 0
