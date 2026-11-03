"""Esquema GraphQL (Strawberry): consultas de ejercicios/progreso y la mutación responder."""
from dataclasses import dataclass
from typing import Callable

import strawberry
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from strawberry.fastapi import BaseContext
from strawberry.types import Info

from mnemo.agentes.tutor import Tutor
from mnemo.analitica.eventos import RegistradorEventos
from mnemo.cognitivo.planificador import planificar_repaso
from mnemo.db import modelos
from mnemo.evaluador.similitud import Evaluacion

NOMBRES_IDIOMA = {"en": "inglés", "fr": "francés", "de": "alemán", "it": "italiano", "pt": "portugués"}


@dataclass
class Contexto(BaseContext):
    """Dependencias que usan los resolvers. Se pueden sustituir en los tests."""

    fabrica_sesiones: sessionmaker[Session]
    evaluar: Callable[[str, list[str]], Evaluacion]
    tutor: Tutor
    registrador: RegistradorEventos | None = None


# --- Tipos GraphQL ---

@strawberry.type
class Ejercicio:
    id: int
    enunciado: str


@strawberry.type
class ResultadoRespuesta:
    puntuacion: float
    veredicto: str
    explicacion: str | None
    solucion: str


@strawberry.type
class ItemRepaso:
    ejercicio: Ejercicio
    probabilidad_recuerdo: float = strawberry.field(
        description="Probabilidad de que el estudiante lo recuerde ahora, según ACT-R")
    practicas: int
    nuevo: bool


@strawberry.type
class Progreso:
    estudiante_id: int
    intentos: int
    correctas: int
    puntuacion_media: float


# --- Consultas ---

@strawberry.type
class Consulta:
    @strawberry.field
    def ejercicios(self, info: Info[Contexto, None], curso_id: int | None = None) -> list[Ejercicio]:
        with info.context.fabrica_sesiones() as sesion:
            consulta = select(modelos.Ejercicio).order_by(modelos.Ejercicio.id)
            if curso_id is not None:
                consulta = consulta.where(modelos.Ejercicio.curso_id == curso_id)
            return [Ejercicio(id=e.id, enunciado=e.enunciado) for e in sesion.scalars(consulta)]

    @strawberry.field
    def progreso(self, info: Info[Contexto, None], estudiante_id: int) -> Progreso:
        with info.context.fabrica_sesiones() as sesion:
            R = modelos.Respuesta
            intentos, correctas, media = sesion.execute(
                select(
                    func.count(R.id),
                    func.count(R.id).filter(R.veredicto == "correcta"),
                    func.coalesce(func.avg(R.puntuacion), 0.0),
                ).where(R.estudiante_id == estudiante_id)
            ).one()
            return Progreso(estudiante_id=estudiante_id, intentos=intentos,
                            correctas=correctas, puntuacion_media=round(float(media), 3))


    @strawberry.field(description="Qué ejercicios repasar ahora: primero los que se están olvidando")
    def repaso(self, info: Info[Contexto, None], estudiante_id: int, limite: int = 10) -> list[ItemRepaso]:
        with info.context.fabrica_sesiones() as sesion:
            return [
                ItemRepaso(ejercicio=Ejercicio(id=i.ejercicio_id, enunciado=i.enunciado),
                           probabilidad_recuerdo=i.probabilidad_recuerdo,
                           practicas=i.practicas, nuevo=i.nuevo)
                for i in planificar_repaso(sesion, estudiante_id, limite=limite)
            ]


# --- Mutaciones ---

@strawberry.type
class Mutacion:
    @strawberry.mutation
    def responder(self, info: Info[Contexto, None], estudiante_id: int,
                  ejercicio_id: int, texto: str) -> ResultadoRespuesta:
        ctx = info.context
        with ctx.fabrica_sesiones() as sesion:
            ejercicio = sesion.get(modelos.Ejercicio, ejercicio_id)
            if ejercicio is None:
                raise ValueError(f"No existe el ejercicio {ejercicio_id}")
            if sesion.get(modelos.Estudiante, estudiante_id) is None:
                raise ValueError(f"No existe el estudiante {estudiante_id}")

            # 1. El evaluador puntúa la respuesta
            evaluacion = ctx.evaluar(texto, ejercicio.soluciones)

            # 2. Si no es correcta, el Tutor explica el error
            explicacion = None
            if evaluacion.veredicto != "correcta":
                explicacion = ctx.tutor.explicar(
                    enunciado=ejercicio.enunciado,
                    respuesta=texto,
                    solucion=evaluacion.solucion_cercana,
                    veredicto=evaluacion.veredicto,
                    puntuacion=evaluacion.puntuacion,
                    idioma_destino=NOMBRES_IDIOMA.get(ejercicio.curso.idioma_destino,
                                                      ejercicio.curso.idioma_destino),
                )

            # 3. Se guarda el intento
            sesion.add(modelos.Respuesta(
                estudiante_id=estudiante_id, ejercicio_id=ejercicio_id, texto=texto,
                puntuacion=evaluacion.puntuacion, veredicto=evaluacion.veredicto,
                explicacion=explicacion,
            ))
            sesion.commit()

        # 4. Evento seudonimizado para la analítica (ClickHouse)
        if ctx.registrador is not None:
            ctx.registrador.registrar_respuesta(
                estudiante_id=estudiante_id, ejercicio_id=ejercicio_id,
                veredicto=evaluacion.veredicto, puntuacion=evaluacion.puntuacion)

        return ResultadoRespuesta(puntuacion=evaluacion.puntuacion, veredicto=evaluacion.veredicto,
                                  explicacion=explicacion, solucion=evaluacion.solucion_cercana)


esquema = strawberry.Schema(query=Consulta, mutation=Mutacion)
