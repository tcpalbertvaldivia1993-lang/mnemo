"""Compara ACT-R con Random Forest para predecir si el alumno recordará un ejercicio.

Uso: python -m mnemo.cognitivo.comparacion
"""
import math
from collections import defaultdict

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from mnemo.cognitivo.actr import ModeloACTR, activacion
from mnemo.cognitivo.simulacion import EventoSimulado, simular_eventos

COLUMNAS = ["practicas_previas", "aciertos_previos", "fallos_previos",
            "log_segundos_desde_ultima", "log_segundos_desde_primera"]


def construir_dataset(eventos: list[EventoSimulado], decaimiento: float = 0.5):
    """Una fila por cada intento evaluado, con lo que se sabía JUSTO antes de él."""
    historial = defaultdict(list)  # (estudiante, item) -> eventos anteriores
    filas, activaciones, etiquetas, grupos = [], [], [], []

    for evento in sorted(eventos, key=lambda e: e.momento):
        previos = historial[(evento.estudiante, evento.item)]
        if evento.acierto is not None and previos:
            momentos = [p.momento for p in previos]
            aciertos = sum(p.acierto == 1 for p in previos)
            fallos = sum(p.acierto == 0 for p in previos)
            filas.append([len(previos), aciertos, fallos,
                          math.log(evento.momento - momentos[-1]),
                          math.log(evento.momento - momentos[0])])
            activaciones.append(activacion(momentos, evento.momento, decaimiento))
            etiquetas.append(evento.acierto)
            grupos.append(evento.estudiante)
        previos.append(evento)

    return (np.array(filas), np.array(activaciones), np.array(etiquetas), np.array(grupos))


def _metricas(y, p) -> dict[str, float]:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"auc": roc_auc_score(y, p), "log_loss": log_loss(y, p), "brier": brier_score_loss(y, p)}


def comparar(eventos: list[EventoSimulado], semilla: int = 0) -> dict:
    x, act, y, grupos = construir_dataset(eventos)

    # Separamos por ESTUDIANTE: el modelo se evalúa con alumnos que no ha visto
    entreno, prueba = next(GroupShuffleSplit(test_size=0.25, random_state=semilla).split(x, y, grupos))

    resultados = {"Base (tasa media de acierto)": _metricas(
        y[prueba], np.full(len(prueba), y[entreno].mean()))}

    actr = ModeloACTR().ajustar(act[entreno], y[entreno])
    p_actr = [actr.predecir_desde_activacion(a) for a in act[prueba]]
    resultados["ACT-R (τ y s ajustados)"] = _metricas(y[prueba], np.array(p_actr))

    bosque = RandomForestClassifier(n_estimators=200, min_samples_leaf=20, n_jobs=-1, random_state=semilla)
    bosque.fit(x[entreno], y[entreno])
    resultados["Random Forest"] = _metricas(y[prueba], bosque.predict_proba(x[prueba])[:, 1])

    x_hibrido = np.column_stack([x, act])
    hibrido = RandomForestClassifier(n_estimators=200, min_samples_leaf=20, n_jobs=-1, random_state=semilla)
    hibrido.fit(x_hibrido[entreno], y[entreno])
    resultados["Random Forest + activación ACT-R"] = _metricas(
        y[prueba], hibrido.predict_proba(x_hibrido[prueba])[:, 1])

    importancias = dict(zip(COLUMNAS + ["activacion_actr"], hibrido.feature_importances_))
    return {"resultados": resultados, "actr": actr, "importancias": importancias,
            "n_entreno": len(entreno), "n_prueba": len(prueba)}


def main() -> None:
    print("Simulando alumnos...")
    salida = comparar(simular_eventos())
    print(f"Intentos: {salida['n_entreno']} de entrenamiento, {salida['n_prueba']} de prueba "
          "(alumnos distintos)\n")
    print(f"{'Modelo':36} {'AUC ↑':>7} {'Log-loss ↓':>11} {'Brier ↓':>8}")
    for nombre, m in salida["resultados"].items():
        print(f"{nombre:36} {m['auc']:7.3f} {m['log_loss']:11.3f} {m['brier']:8.3f}")

    print("\nImportancia de cada variable en el Random Forest + ACT-R:")
    for nombre, valor in sorted(salida["importancias"].items(), key=lambda kv: -kv[1]):
        print(f"  {nombre:28} {valor:.3f}")

    actr = salida["actr"]
    print(f"\nParámetros de ACT-R ajustados (puedes ponerlos en .env):\n"
          f"  ACTR_UMBRAL={actr.umbral:.2f}\n  ACTR_RUIDO={actr.ruido:.2f}")


if __name__ == "__main__":
    main()
