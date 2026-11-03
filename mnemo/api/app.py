"""Aplicación web. Uso: uvicorn mnemo.api.app:app --reload  →  http://localhost:8000/graphql"""
import logging
from typing import Callable

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker
from strawberry.fastapi import GraphQLRouter

from mnemo.agentes.tutor import Tutor
from mnemo.analitica.eventos import RegistradorEventos
from mnemo.api.esquema import Contexto, esquema
from mnemo.evaluador.similitud import Evaluacion

log = logging.getLogger(__name__)


def crear_app(fabrica_sesiones: sessionmaker[Session] | None = None,
              evaluar: Callable[[str, list[str]], Evaluacion] | None = None,
              tutor: Tutor | None = None,
              registrador: RegistradorEventos | None = None) -> FastAPI:
    """Crea la app con las dependencias dadas (los tests pasan versiones simuladas)."""
    if fabrica_sesiones is None:
        from mnemo.db.sesion import FabricaSesiones, crear_tablas

        crear_tablas()
        fabrica_sesiones = FabricaSesiones
    if evaluar is None:
        from mnemo.evaluador.similitud import evaluar
    tutor = tutor or Tutor()

    def obtener_contexto() -> Contexto:
        # Un contexto nuevo por petición (Strawberry le añade la petición HTTP).
        return Contexto(fabrica_sesiones=fabrica_sesiones, evaluar=evaluar, tutor=tutor,
                        registrador=registrador)

    app = FastAPI(title="Mnemo")
    app.include_router(GraphQLRouter(esquema, context_getter=obtener_contexto), prefix="/graphql")
    return app


def crear_registrador_clickhouse() -> RegistradorEventos | None:
    """Conecta con ClickHouse. Si no está disponible, la app funciona sin analítica."""
    from mnemo.analitica.eventos import RegistradorClickHouse
    from mnemo.privacidad.seudonimos import Seudonimizador

    try:
        return RegistradorClickHouse(Seudonimizador())
    except Exception as error:
        log.warning("Analítica desactivada (ClickHouse no disponible o falta configuración): %s", error)
        return None


def __getattr__(nombre: str):
    # `app` se crea solo cuando uvicorn lo pide, para que importar este módulo
    # en los tests no intente conectarse a Postgres ni a ClickHouse.
    if nombre == "app":
        global app
        app = crear_app(registrador=crear_registrador_clickhouse())
        return app
    raise AttributeError(nombre)
