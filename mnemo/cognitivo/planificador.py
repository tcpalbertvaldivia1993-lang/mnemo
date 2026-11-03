"""Planificador de repasos: ordena los ejercicios por lo cerca que están de olvidarse.

Lee el historial de Postgres (datos de la aplicación) y aplica el modelo ACT-R.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemo.cognitivo.actr import ModeloACTR
from mnemo.config import obtener_configuracion
from mnemo.db import modelos


@dataclass
class ItemRepaso:
    ejercicio_id: int
    enunciado: str
    probabilidad_recuerdo: float
    practicas: int

    @property
    def nuevo(self) -> bool:
        return self.practicas == 0


def _en_utc(momento: datetime) -> datetime:
    # SQLite devuelve fechas sin zona horaria; las tratamos como UTC
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def planificar_repaso(sesion: Session, estudiante_id: int, *, modelo: ModeloACTR | None = None,
                      ahora: datetime | None = None, limite: int = 10,
                      incluir_nuevos: bool = True) -> list[ItemRepaso]:
    """Ejercicios por debajo del umbral de repaso, del más olvidado al menos.

    Los ejercicios ya practicados que se están olvidando van primero; después, los nuevos.
    """
    modelo = modelo or ModeloACTR()
    ahora = ahora or datetime.now(timezone.utc)
    umbral = obtener_configuracion().umbral_repaso

    practicas: dict[int, list[datetime]] = defaultdict(list)
    for ejercicio_id, momento in sesion.execute(
        select(modelos.Respuesta.ejercicio_id, modelos.Respuesta.creado_en)
        .where(modelos.Respuesta.estudiante_id == estudiante_id)
    ):
        practicas[ejercicio_id].append(_en_utc(momento))

    repasar, nuevos = [], []
    for ejercicio in sesion.scalars(select(modelos.Ejercicio).order_by(modelos.Ejercicio.id)):
        historial = practicas.get(ejercicio.id, [])
        if not historial:
            if incluir_nuevos:
                nuevos.append(ItemRepaso(ejercicio.id, ejercicio.enunciado, 0.0, 0))
            continue
        p = modelo.predecir(historial, ahora)
        if p < umbral:
            repasar.append(ItemRepaso(ejercicio.id, ejercicio.enunciado, round(p, 3), len(historial)))

    repasar.sort(key=lambda item: item.probabilidad_recuerdo)
    return (repasar + nuevos)[:limite]
