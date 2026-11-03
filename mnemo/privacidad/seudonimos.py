"""Seudonimización de estudiantes para la analítica (en la línea de FERPA).

FERPA es una ley de EE. UU. que protege los registros educativos. La analítica
(ClickHouse) no necesita saber QUIÉN es el estudiante, solo poder agrupar sus
eventos. Por eso guardamos un seudónimo en lugar del ID real.

¿Por qué HMAC y no un simple SHA-256? Los IDs son números pequeños (1, 2, 3...):
cualquiera podría calcular sha256("1"), sha256("2")... y deshacer el seudónimo.
Con HMAC hace falta además la clave secreta, que solo tiene la aplicación.

Ojo: seudonimizar es una medida de protección, no garantiza por sí sola el
cumplimiento legal (también cuentan el consentimiento, los accesos, etc.).
"""
import hashlib
import hmac

from mnemo.config import obtener_configuracion


class Seudonimizador:
    def __init__(self, clave: str | None = None):
        clave = clave if clave is not None else obtener_configuracion().clave_seudonimos
        if len(clave) < 32:
            raise ValueError("CLAVE_SEUDONIMOS falta o es demasiado corta (mínimo 32 caracteres). "
                             "Genera una con: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
        self._clave = clave.encode()

    def seudonimo(self, estudiante_id: int) -> str:
        """Siempre devuelve el mismo seudónimo para el mismo estudiante y la misma clave."""
        mensaje = f"estudiante:{estudiante_id}".encode()
        return hmac.new(self._clave, mensaje, hashlib.sha256).hexdigest()
