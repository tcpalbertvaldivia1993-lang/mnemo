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

    # ClickHouse (analítica de eventos)
    clickhouse_host: str = "localhost"
    clickhouse_puerto: int = 8123
    clickhouse_usuario: str = "mnemo"
    clickhouse_password: str = "mnemo"
    clickhouse_base: str = "mnemo"

    # Clave secreta para seudonimizar a los estudiantes (HMAC). Generarla con:
    # python3 -c "import secrets; print(secrets.token_hex(32))"
    clave_seudonimos: str = ""

    # Parámetros de ACT-R (tiempo en segundos). Los valores por defecto salen de ajustar
    # el modelo a alumnos SIMULADOS (python -m mnemo.cognitivo.comparacion); con datos
    # reales habría que volver a ajustarlos.
    actr_decaimiento: float = 0.5  # d: lo rápido que se olvida
    actr_umbral: float = -4.5  # τ: activación con la que se recuerda el 50 % de las veces
    actr_ruido: float = 0.45  # s: cuánto varía el recuerdo de una vez a otra
    umbral_repaso: float = 0.9  # se repasa lo que tenga menos de un 90 % de probabilidad

    # Similitud coseno mínima para considerar que el significado es el mismo ("casi").
    # Solo es "correcta" una coincidencia con una solución válida: los embeddings
    # miden significado, no gramática ("I have hungry" ≈ "I am hungry": 0.98).
    umbral_casi: float = 0.80


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
