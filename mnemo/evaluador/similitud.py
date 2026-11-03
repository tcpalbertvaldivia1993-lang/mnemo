"""Evaluador semántico: compara la respuesta con las soluciones válidas usando embeddings."""
import re
from dataclasses import dataclass
from functools import lru_cache

from mnemo.config import obtener_configuracion


@dataclass
class Evaluacion:
    puntuacion: float  # similitud coseno máxima (0 a 1)
    veredicto: str  # "correcta", "casi" o "incorrecta"
    solucion_cercana: str  # la solución más parecida a la respuesta


@lru_cache
def _modelo():
    # Importación diferida: cargar torch tarda, así que solo se hace cuando hace falta.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(obtener_configuracion().modelo_embeddings)


def _normalizar(texto: str) -> str:
    """Minúsculas, sin puntuación ni apóstrofos: "I'm hungry." → "im hungry"."""
    sin_puntuacion = re.sub(r"[^\w\s]", "", texto.lower())
    return " ".join(sin_puntuacion.split())


def decidir_veredicto(puntuacion: float) -> str:
    """Para respuestas que NO coinciden con ninguna solución válida."""
    if puntuacion >= obtener_configuracion().umbral_casi:
        return "casi"  # mismo significado, pero la forma (gramática, palabras) falla
    return "incorrecta"


def evaluar(respuesta: str, soluciones: list[str]) -> Evaluacion:
    """Devuelve la evaluación de una traducción libre."""
    # Solo es correcta si coincide con una solución (ignorando mayúsculas y puntuación).
    for solucion in soluciones:
        if _normalizar(respuesta) == _normalizar(solucion):
            return Evaluacion(1.0, "correcta", solucion)

    from sentence_transformers import util

    modelo = _modelo()
    emb_respuesta = modelo.encode(respuesta, convert_to_tensor=True)
    emb_soluciones = modelo.encode(soluciones, convert_to_tensor=True)
    similitudes = util.cos_sim(emb_respuesta, emb_soluciones)[0]

    indice = int(similitudes.argmax())
    puntuacion = float(similitudes[indice])
    return Evaluacion(round(puntuacion, 3), decidir_veredicto(puntuacion), soluciones[indice])
