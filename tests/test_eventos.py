from datetime import datetime, timezone

import pytest

from mnemo.analitica.eventos import RegistradorClickHouse, RegistradorEventos, RegistradorMemoria
from mnemo.privacidad.seudonimos import Seudonimizador

SEUDO = Seudonimizador("c" * 64)


def test_evento_seudonimizado_y_sin_texto():
    registrador = RegistradorMemoria(SEUDO)
    registrador.registrar_respuesta(estudiante_id=42, ejercicio_id=3, veredicto="casi", puntuacion=0.9)
    evento = registrador.eventos[0]
    assert evento.seudonimo == SEUDO.seudonimo(42)
    assert not hasattr(evento, "estudiante_id") and not hasattr(evento, "texto")
    assert evento.correcta == 0


def test_un_fallo_de_la_analitica_no_rompe_nada():
    class Roto(RegistradorEventos):
        def _guardar(self, evento):
            raise ConnectionError("ClickHouse caído")

    Roto(SEUDO).registrar_respuesta(estudiante_id=1, ejercicio_id=1, veredicto="correcta", puntuacion=1.0)


def test_clickhouse_real():
    """Test de integración: se salta si ClickHouse no está arrancado (por ejemplo en GitHub Actions)."""
    from mnemo.analitica.eventos import crear_cliente

    try:
        cliente = crear_cliente()
        cliente.ping()
    except Exception:
        pytest.skip("ClickHouse no disponible")

    registrador = RegistradorClickHouse(SEUDO, cliente)
    momento = datetime(2000, 1, 1, tzinfo=timezone.utc)  # fecha marcada para borrar después
    registrador.registrar_respuesta(estudiante_id=99, ejercicio_id=1, veredicto="correcta",
                                    puntuacion=1.0, momento=momento)
    filas = cliente.query("SELECT seudonimo, correcta FROM eventos_respuesta "
                          "WHERE momento = '2000-01-01 00:00:00'").result_rows
    cliente.command("DELETE FROM eventos_respuesta WHERE momento = '2000-01-01 00:00:00'")
    assert (SEUDO.seudonimo(99), 1) in filas
