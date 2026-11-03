"""Alumnos simulados para probar los modelos de memoria sin datos reales.

Para que la comparación sea justa, los alumnos NO se simulan con ACT-R, sino con
otro modelo de olvido: cada recuerdo tiene una "vida media" h que crece con cada
acierto y baja con cada fallo, y P(recuerdo) = 2^(-Δt / h).
"""
from dataclasses import dataclass

import numpy as np

HORA = 3600.0
DIA = 24 * HORA


@dataclass
class EventoSimulado:
    estudiante: int
    item: int
    momento: float  # segundos desde el inicio
    acierto: int | None  # None en la primera exposición (aprendizaje, sin evaluar)


def simular_eventos(n_estudiantes: int = 300, n_items: int = 20, semilla: int = 0) -> list[EventoSimulado]:
    rng = np.random.default_rng(semilla)
    habilidad = rng.normal(0, 0.5, n_estudiantes)
    dificultad = rng.normal(0, 0.5, n_items)
    eventos = []

    for estudiante in range(n_estudiantes):
        for item in range(n_items):
            vida_media = 6 * HORA * np.exp(habilidad[estudiante] - dificultad[item])
            momento = rng.uniform(0, 7 * DIA)
            eventos.append(EventoSimulado(estudiante, item, momento, None))

            for _ in range(rng.integers(3, 10)):
                # Intervalos entre 10 minutos y 2 semanas (escala logarítmica)
                intervalo = float(np.exp(rng.uniform(np.log(600), np.log(14 * DIA))))
                momento += intervalo
                acierto = int(rng.random() < 2 ** (-intervalo / vida_media))
                eventos.append(EventoSimulado(estudiante, item, momento, acierto))
                vida_media *= 2.5 if acierto else 0.7

    return eventos
