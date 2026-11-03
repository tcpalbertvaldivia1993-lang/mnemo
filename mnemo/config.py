"""Configuración de Mnemo, leída de variables de entorno o del archivo .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mnemo:mnemo@localhost:5433/mnemo"

    # LLM del Tutor: "ollama" (gratis, local), "anthropic" (de pago) o "falso" (respuestas fijas)
    proveedor_llm: str = "ollama"
    modelo_ollama: str = "qwen2.5:3b"
    url_ollama: str = "http://localhost:11434"
    anthropic_api_key: str = ""
    modelo_anthropic: str = "claude-sonnet-5-5"
    modelo_embeddings: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Similitud coseno mínima para considerar que el significado es el mismo ("casi").
    # Solo es "correcta" una coincidencia con una solución válida: los embeddings
    # miden significado, no gramática ("I have hungry" ≈ "I am hungry": 0.98).
    umbral_casi: float = 0.80


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
