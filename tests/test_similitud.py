"""Tests del evaluador. Los que usan el modelo real lo descargan la primera vez (~500 MB)."""
from mnemo.evaluador.similitud import decidir_veredicto, evaluar


def test_coincidencia_exacta_ignora_mayusculas_y_punto():
    resultado = evaluar("i'm hungry.", ["I am hungry", "I'm hungry"])
    assert resultado.veredicto == "correcta"
    assert resultado.puntuacion == 1.0


def test_apostrofo_omitido_es_correcta():
    assert evaluar("Im hungry", ["I'm hungry"]).veredicto == "correcta"


def test_umbrales():
    assert decidir_veredicto(0.9) == "casi"
    assert decidir_veredicto(0.5) == "incorrecta"


def test_error_gramatical_no_es_correcta():
    # Mismo significado, gramática mal: debe ir al Tutor como "casi"
    assert evaluar("I have hungry", ["I am hungry", "I'm hungry"]).veredicto == "casi"


def test_significado_distinto_es_incorrecta():
    assert evaluar("I am angry", ["I am hungry", "I'm hungry"]).veredicto == "incorrecta"


def test_parafrasis_puntua_mas_que_frase_sin_relacion():
    soluciones = ["Where is the train station?"]
    parecida = evaluar("Where's the railway station?", soluciones)
    distinta = evaluar("My cat likes fish", soluciones)
    assert parecida.puntuacion > distinta.puntuacion
    assert distinta.veredicto == "incorrecta"
