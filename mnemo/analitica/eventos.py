"""Registro de eventos de respuesta para analítica (ClickHouse).

Cada vez que un estudiante responde, se guarda un evento. Por privacidad:
- el estudiante va SEUDONIMIZADO (ver mnemo.privacidad.seudonimos);
- NO se guarda el texto que escribió (podría contener datos personales).
"""
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from mnemo.config import obtener_configuracion
from mnemo.privacidad.seudonimos import Seudonimizador

log = logging.getLogger(__name__)

TABLA = "eventos_respuesta"

CREAR_TABLA = f"""
CREATE TABLE IF NOT EXISTS {TABLA} (
    seudonimo    String,
    ejercicio_id UInt32,
    correcta     UInt8,
    veredicto    LowCardinality(String),
    puntuacion   Float32,
    momento      DateTime64(3, 'UTC')
)
ENGINE = MergeTree
ORDER BY (seudonimo, ejercicio_id, momento)
"""


@dataclass
class EventoRespuesta:
    seudonimo: str
    ejercicio_id: int
    correcta: int
    veredicto: str
    puntuacion: float
    momento: datetime


class RegistradorEventos:
    """Clase base: seudonimiza y delega el guardado en `_guardar`."""

    def __init__(self, seudonimizador: Seudonimizador):
        self._seudonimizador = seudonimizador

    def registrar_respuesta(self, *, estudiante_id: int, ejercicio_id: int, veredicto: str,
                            puntuacion: float, momento: datetime | None = None) -> None:
        evento = EventoRespuesta(
            seudonimo=self._seudonimizador.seudonimo(estudiante_id),
            ejercicio_id=ejercicio_id,
            correcta=int(veredicto == "correcta"),
            veredicto=veredicto,
            puntuacion=puntuacion,
            momento=momento or datetime.now(timezone.utc),
        )
        try:
            self._guardar(evento)
        except Exception:
            # La analítica no debe romper la experiencia del estudiante.
            log.warning("No se pudo registrar el evento en la analítica", exc_info=True)

    def _guardar(self, evento: EventoRespuesta) -> None:
        raise NotImplementedError


class RegistradorMemoria(RegistradorEventos):
    """Guarda los eventos en una lista. Útil para tests."""

    def __init__(self, seudonimizador: Seudonimizador):
        super().__init__(seudonimizador)
        self.eventos: list[EventoRespuesta] = []

    def _guardar(self, evento: EventoRespuesta) -> None:
        self.eventos.append(evento)


class RegistradorClickHouse(RegistradorEventos):
    def __init__(self, seudonimizador: Seudonimizador, cliente=None):
        super().__init__(seudonimizador)
        self._cliente = cliente or crear_cliente()
        self._cliente.command(CREAR_TABLA)

    def _guardar(self, evento: EventoRespuesta) -> None:
        fila = asdict(evento)
        columnas = list(fila)
        self._cliente.insert(TABLA, [list(fila.values())], column_names=columnas)


def crear_cliente():
    import clickhouse_connect

    config = obtener_configuracion()
    return clickhouse_connect.get_client(
        host=config.clickhouse_host, port=config.clickhouse_puerto,
        username=config.clickhouse_usuario, password=config.clickhouse_password,
        database=config.clickhouse_base,
    )
