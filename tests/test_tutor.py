"""Tests de la elección de proveedor del LLM (no llaman a ningún modelo real)."""
import pytest

from mnemo.agentes import tutor
from mnemo.config import Configuracion


def usar_config(monkeypatch, **valores):
    monkeypatch.setattr(tutor, "obtener_configuracion", lambda: Configuracion(_env_file=None, **valores))


def test_proveedor_ollama(monkeypatch):
    usar_config(monkeypatch, proveedor_llm="ollama", modelo_ollama="qwen2.5:3b")
    llm = tutor.crear_llm()
    assert type(llm).__name__ == "ChatOllama"
    assert llm.model == "qwen2.5:3b"


def test_proveedor_falso_explica(monkeypatch):
    usar_config(monkeypatch, proveedor_llm="falso")
    texto = tutor.Tutor().explicar(enunciado="Tengo hambre", respuesta="I have hungry",
                                   solucion="I am hungry", veredicto="casi", puntuacion=0.98)
    assert "Tutor simulado" in texto


def test_anthropic_sin_clave_da_error(monkeypatch):
    usar_config(monkeypatch, proveedor_llm="anthropic", anthropic_api_key="")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        tutor.crear_llm()


def test_proveedor_desconocido(monkeypatch):
    usar_config(monkeypatch, proveedor_llm="inventado")
    with pytest.raises(ValueError, match="desconocido"):
        tutor.crear_llm()


def test_diferencias_palabra_cambiada():
    assert tutor.describir_diferencias("I have hungry", "I am hungry") == 'Usó "have" en vez de "am".'


def test_diferencias_palabra_que_falta_y_sobra():
    assert tutor.describir_diferencias("I hungry", "I am hungry") == 'Falta: "am".'
    assert tutor.describir_diferencias("I am very hungry", "I am hungry") == 'Sobra: "very".'


def test_diferencias_orden():
    assert tutor.describir_diferencias("The house red", "The red house") == \
        "Mismas palabras, pero en distinto orden."


def test_plantilla_incluye_ejemplos_y_diferencias():
    mensajes = tutor.PLANTILLA.format_messages(
        idioma_destino="inglés", enunciado="Tengo hambre", respuesta="I have hungry",
        solucion="I am hungry", diferencias='Usó "have" en vez de "am".', veredicto="casi")
    # sistema + 3 ejemplos (pregunta y respuesta) + el caso real
    assert len(mensajes) == 1 + 2 * len(tutor.EJEMPLOS) + 1
    assert 'Usó "have" en vez de "am".' in mensajes[-1].content
