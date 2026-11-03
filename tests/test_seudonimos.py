import pytest

from mnemo.privacidad.seudonimos import Seudonimizador

CLAVE = "a" * 64


def test_mismo_estudiante_mismo_seudonimo():
    s = Seudonimizador(CLAVE)
    assert s.seudonimo(7) == s.seudonimo(7)
    assert len(s.seudonimo(7)) == 64


def test_estudiantes_distintos_seudonimos_distintos():
    s = Seudonimizador(CLAVE)
    assert s.seudonimo(1) != s.seudonimo(2)


def test_sin_la_clave_no_se_puede_deshacer():
    # Con otra clave, el seudónimo del mismo estudiante es otro
    assert Seudonimizador(CLAVE).seudonimo(1) != Seudonimizador("b" * 64).seudonimo(1)


def test_no_es_un_sha256_simple():
    import hashlib

    s = Seudonimizador(CLAVE).seudonimo(1)
    assert s not in {hashlib.sha256(t.encode()).hexdigest() for t in ["1", "estudiante:1"]}


def test_clave_corta_da_error():
    with pytest.raises(ValueError, match="CLAVE_SEUDONIMOS"):
        Seudonimizador("corta")
