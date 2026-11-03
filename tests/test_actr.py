import math

import numpy as np
import pytest

from mnemo.cognitivo.actr import ModeloACTR, activacion, probabilidad_recuerdo

HORA, DIA = 3600, 86400


def test_activacion_coincide_con_la_formula():
    # A = ln(Σ t^-d) con prácticas hace 1 h y hace 1 día
    esperado = math.log(HORA ** -0.5 + DIA ** -0.5)
    assert activacion([DIA * 9, DIA * 10 - HORA], DIA * 10) == pytest.approx(esperado)


def test_sin_practicas_la_activacion_es_menos_infinito():
    assert activacion([], 100) == -math.inf
    assert probabilidad_recuerdo(-math.inf, -4.5, 0.45) == 0.0


def test_el_tiempo_hace_olvidar():
    modelo = ModeloACTR(umbral=-4.5, ruido=0.45)
    assert modelo.predecir([0], HORA) > modelo.predecir([0], DIA) > modelo.predecir([0], 30 * DIA)


def test_practicar_mas_ayuda_a_recordar():
    modelo = ModeloACTR(umbral=-4.5, ruido=0.45)
    ahora = 10 * DIA
    assert modelo.predecir([0, DIA, 2 * DIA], ahora) > modelo.predecir([0], ahora)


def test_umbral_da_probabilidad_del_50_por_ciento():
    assert probabilidad_recuerdo(-4.5, umbral=-4.5, ruido=0.45) == pytest.approx(0.5)


def test_ajustar_recupera_los_parametros():
    rng = np.random.default_rng(0)
    activaciones = rng.uniform(-8, -2, 20000)
    aciertos = rng.random(20000) < [probabilidad_recuerdo(a, -5.0, 0.6) for a in activaciones]
    modelo = ModeloACTR().ajustar(activaciones, aciertos.astype(int))
    assert modelo.umbral == pytest.approx(-5.0, abs=0.1)
    assert modelo.ruido == pytest.approx(0.6, abs=0.05)
