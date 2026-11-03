"""Tests de la API GraphQL con evaluador y Tutor simulados (no gastan API ni descargan modelos)."""
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import FakeListChatModel

from mnemo.agentes.tutor import Tutor
from mnemo.analitica.eventos import RegistradorMemoria
from mnemo.api.app import crear_app
from mnemo.evaluador.similitud import Evaluacion
from mnemo.privacidad.seudonimos import Seudonimizador


def evaluador_falso(respuesta: str, soluciones: list[str]) -> Evaluacion:
    if respuesta in soluciones:
        return Evaluacion(1.0, "correcta", respuesta)
    return Evaluacion(0.4, "incorrecta", soluciones[0])


@pytest.fixture
def registrador():
    return RegistradorMemoria(Seudonimizador("d" * 64))


@pytest.fixture
def cliente(fabrica_sesiones, registrador):
    tutor = Tutor(llm=FakeListChatModel(responses=["Recuerda que en inglés se usa el verbo 'to be'."]))
    return TestClient(crear_app(fabrica_sesiones, evaluador_falso, tutor, registrador))


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


def test_responder_registra_evento_seudonimizado(cliente, registrador):
    graphql(cliente, 'mutation { responder(estudianteId: 1, ejercicioId: 2, texto: "x") { veredicto } }')
    assert len(registrador.eventos) == 1
    evento = registrador.eventos[0]
    assert evento.ejercicio_id == 2 and evento.veredicto == "incorrecta"
    assert evento.seudonimo == Seudonimizador("d" * 64).seudonimo(1)


def test_repaso(cliente):
    graphql(cliente, 'mutation { responder(estudianteId: 1, ejercicioId: 1, texto: "I am hungry") '
                     "{ veredicto } }")
    datos = graphql(cliente, "{ repaso(estudianteId: 1) { ejercicio { id } probabilidadRecuerdo nuevo } }")
    # El ejercicio 1 se acaba de practicar: no hace falta repasarlo todavía
    ids = [item["ejercicio"]["id"] for item in datos["repaso"]]
    assert ids == [2, 3, 4, 5]
    assert all(item["nuevo"] for item in datos["repaso"])
