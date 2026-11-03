"""Carga datos de ejemplo. Uso: python -m mnemo.db.semilla"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemo.db.modelos import Curso, Ejercicio, Estudiante

EJERCICIOS_EJEMPLO = [
    ("Tengo hambre", ["I am hungry", "I'm hungry"]),
    ("¿Dónde está la estación de tren?", ["Where is the train station?"]),
    ("Me gusta leer libros", ["I like reading books", "I like to read books"]),
    ("Hace frío hoy", ["It is cold today", "It's cold today"]),
    ("Mi hermana trabaja en un hospital", ["My sister works in a hospital", "My sister works at a hospital"]),
]


def cargar_semilla(sesion: Session) -> None:
    """Inserta un estudiante, un curso y ejercicios, si aún no existen."""
    if sesion.scalar(select(Curso).limit(1)) is not None:
        print("La base de datos ya tiene datos; no se carga la semilla.")
        return

    curso = Curso(nombre="Inglés para hispanohablantes", idioma_origen="es", idioma_destino="en")
    curso.ejercicios = [Ejercicio(enunciado=e, soluciones=s) for e, s in EJERCICIOS_EJEMPLO]
    sesion.add_all([curso, Estudiante(nombre="Estudiante de prueba")])
    sesion.commit()
    print(f"Semilla cargada: {len(EJERCICIOS_EJEMPLO)} ejercicios.")


if __name__ == "__main__":
    from mnemo.db.sesion import FabricaSesiones, crear_tablas

    crear_tablas()
    with FabricaSesiones() as sesion:
        cargar_semilla(sesion)
