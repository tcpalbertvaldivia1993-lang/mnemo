"""Modelo de memoria ACT-R: ¿qué probabilidad hay de que el estudiante recuerde un ejercicio?

ACT-R es una teoría de la cognición humana. Cada recuerdo tiene una ACTIVACIÓN:

    A = ln( Σ t_j^(-d) )

donde t_j son los segundos transcurridos desde cada vez que se practicó y d es el
decaimiento (0.5 por defecto). Practicar más sube la activación; el paso del
tiempo la baja. La probabilidad de recordarlo es una curva logística:

    P(recuerdo) = 1 / (1 + e^(-(A - τ) / s))

τ (umbral) es la activación con la que se recuerda el 50 % de las veces y
s (ruido) controla lo brusca que es la curva.
"""
import math
import warnings
from collections.abc import Sequence
from datetime import datetime

import numpy as np

from mnemo.config import obtener_configuracion

with warnings.catch_warnings():
    # pyactr es una librería antigua y avisa de escapes inválidos al importarse
    warnings.simplefilter("ignore", SyntaxWarning)
    from pyactr.utilities import baselevel_learning

SEGUNDOS_MINIMOS = 1.0  # evita dividir entre cero si se practicó "ahora mismo"


def _segundos(momento: datetime | float) -> float:
    return momento.timestamp() if isinstance(momento, datetime) else float(momento)


def activacion(practicas: Sequence[datetime | float], ahora: datetime | float,
               decaimiento: float = 0.5) -> float:
    """Activación base de ACT-R calculada con PyACTR. -inf si nunca se practicó."""
    t_ahora = _segundos(ahora)
    tiempos = [_segundos(p) for p in practicas if _segundos(p) < t_ahora]
    if not tiempos:
        return -math.inf
    # Si una práctica es casi "ahora", la tratamos como de hace 1 segundo
    tiempos = np.minimum(np.array(tiempos), t_ahora - SEGUNDOS_MINIMOS)
    return float(baselevel_learning(t_ahora, tiempos, bll=True, decay=decaimiento))


def probabilidad_recuerdo(activacion_: float, umbral: float, ruido: float) -> float:
    if activacion_ == -math.inf:
        return 0.0
    z = (activacion_ - umbral) / ruido
    return 1 / (1 + math.exp(-z)) if z > -700 else 0.0


class ModeloACTR:
    def __init__(self, decaimiento: float | None = None, umbral: float | None = None,
                 ruido: float | None = None):
        config = obtener_configuracion()
        self.decaimiento = config.actr_decaimiento if decaimiento is None else decaimiento
        self.umbral = config.actr_umbral if umbral is None else umbral
        self.ruido = config.actr_ruido if ruido is None else ruido

    def activacion(self, practicas, ahora) -> float:
        return activacion(practicas, ahora, self.decaimiento)

    def predecir(self, practicas, ahora) -> float:
        return self.predecir_desde_activacion(self.activacion(practicas, ahora))

    def predecir_desde_activacion(self, activacion_: float) -> float:
        return probabilidad_recuerdo(activacion_, self.umbral, self.ruido)

    def ajustar(self, activaciones: Sequence[float], aciertos: Sequence[int]) -> "ModeloACTR":
        """Ajusta τ y s a datos reales con una regresión logística sobre la activación.

        La logística da P = 1/(1+e^-(a·A + b)); comparando con la fórmula de ACT-R:
        s = 1/a  y  τ = -b/a.
        """
        from sklearn.linear_model import LogisticRegression

        x = np.array(activaciones, dtype=float).reshape(-1, 1)
        regresion = LogisticRegression(C=1e6).fit(x, np.array(aciertos))
        a, b = float(regresion.coef_[0][0]), float(regresion.intercept_[0])
        if a <= 0:
            raise ValueError("Los datos no muestran que más activación implique más recuerdo")
        self.ruido, self.umbral = 1 / a, -b / a
        return self
