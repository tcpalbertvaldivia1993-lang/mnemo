"""Tests de la API GraphQL con evaluador y Tutor simulados (no gastan API ni descargan modelos)."""
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import FakeListChatModel

from mnemo.agentes.tutor import Tutor
from mnemo.api.app import crear_app
from mnemo.evaluador.similitud import Evaluacion


def evaluador_falso(respuesta: str, soluciones: list[str]) -> Evaluacion:
    if respuesta in soluciones:
        return Evaluacion(1.0, "correcta", respuesta)
    return Evaluacion(0.4, "incorrecta", soluciones[0])


@pytest.fixture
def cliente(fabrica_sesiones):
    tutor = Tutor(llm=FakeListChatModel(responses=["Recuerda que en inglés se usa el verbo 'to be'."]))
    return TestClient(crear_app(fabrica_sesiones, evaluador_falso, tutor))


def graphql(cliente, consulta: str) -> dict:
    respuesta = cliente.post("/graphql", json={"query": consulta})
    cuerpo = respuesta.json()
    assert "errors" not in cuerpo, cuerpo
    return cuerpo["data"]


def test_lista_ejercicios(cliente):
    datos = graphql(cliente, "{ ejercicios { id enunciado } }")
    assert datos["ejercicios"][0] == {"id": 1, "enunciado": "Tengo hambre"}


def test_respuesta_correcta_no_llama_al_tutor(cliente):
    datos = graphql(cliente, 'mutation { responder(estudianteId: 1, ejercicioId: 1, texto: "I am hungry") '
                             "{ veredicto explicacion } }")
    assert datos["responder"] == {"veredicto": "correcta", "explicacion": None}


def test_respuesta_incorrecta_trae_explicacion_y_cuenta_en_progreso(cliente):
    datos = graphql(cliente, 'mutation { responder(estudianteId: 1, ejercicioId: 1, texto: "I have hungry") '
                             "{ veredicto explicacion solucion } }")
    assert datos["responder"]["veredicto"] == "incorrecta"
    assert "to be" in datos["responder"]["explicacion"]

    progreso = graphql(cliente, "{ progreso(estudianteId: 1) { intentos correctas } }")
    assert progreso["progreso"] == {"intentos": 1, "correctas": 0}


def test_ejercicio_inexistente_da_error(cliente):
    respuesta = cliente.post("/graphql", json={"query":
        'mutation { responder(estudianteId: 1, ejercicioId: 999, texto: "x") { veredicto } }'})
    assert "No existe el ejercicio 999" in respuesta.json()["errors"][0]["message"]
