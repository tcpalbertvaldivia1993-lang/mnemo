from datetime import datetime, timedelta, timezone

from mnemo.cognitivo.actr import ModeloACTR
from mnemo.cognitivo.planificador import planificar_repaso
from mnemo.db.modelos import Respuesta

AHORA = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)


def practicar(sesion, ejercicio_id, hace: timedelta):
    sesion.add(Respuesta(estudiante_id=1, ejercicio_id=ejercicio_id, texto="x", puntuacion=1.0,
                         veredicto="correcta", creado_en=AHORA - hace))


def test_ordena_por_olvido_y_deja_nuevos_al_final(fabrica_sesiones):
    with fabrica_sesiones() as sesion:
        practicar(sesion, 1, timedelta(days=20))   # muy olvidado
        practicar(sesion, 2, timedelta(days=2))    # algo olvidado
        practicar(sesion, 3, timedelta(minutes=1))  # recién practicado: no hace falta repasar
        sesion.commit()

        items = planificar_repaso(sesion, 1, modelo=ModeloACTR(umbral=-4.5, ruido=0.45), ahora=AHORA)

    ids = [i.ejercicio_id for i in items]
    assert ids[:2] == [1, 2]
    assert 3 not in ids
    assert ids[2:] == [4, 5] and all(i.nuevo for i in items[2:])
    assert items[0].probabilidad_recuerdo < items[1].probabilidad_recuerdo < 0.9


def test_limite(fabrica_sesiones):
    with fabrica_sesiones() as sesion:
        assert len(planificar_repaso(sesion, 1, ahora=AHORA, limite=2)) == 2
