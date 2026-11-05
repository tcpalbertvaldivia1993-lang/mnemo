import pytest

from mnemo.cognitivo.actr import ModeloACTR
from mnemo.laboratorio import (barra, curva_de_olvido, leer_duraciones, romper_por_fuerza_bruta,
                               seudonimo_hmac, seudonimo_sha256)


def test_leer_duraciones():
    assert leer_duraciones("1d 2h 30m 10s 1sem 1,5h") == [86400, 7200, 1800, 10, 604800, 5400]


@pytest.mark.parametrize("texto", ["", "ayer", "3x", "3d hola"])
def test_duraciones_no_validas(texto):
    with pytest.raises(ValueError):
        leer_duraciones(texto)


def test_la_curva_baja_con_el_tiempo():
    curva = curva_de_olvido([3600], ModeloACTR(umbral=-4.5, ruido=0.45))
    probabilidades = [p for _, _, p in curva]
    assert probabilidades == sorted(probabilidades, reverse=True)
    assert probabilidades[0] == pytest.approx(0.711, abs=0.001)  # el valor de 1 hora


def test_barra():
    assert barra(0.5, ancho=4) == "██░░"


def test_sha256_se_rompe_y_hmac_con_otra_clave_no():
    assert romper_por_fuerza_bruta(seudonimo_sha256(50), seudonimo_sha256, limite=100) == 50
    objetivo = seudonimo_hmac(b"r" * 32, 50)
    assert romper_por_fuerza_bruta(objetivo, lambda i: seudonimo_hmac(b"x" * 32, i), limite=100) is None
    assert romper_por_fuerza_bruta(objetivo, lambda i: seudonimo_hmac(b"r" * 32, i), limite=100) == 50
