"""Conexión a la base de datos."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mnemo.config import obtener_configuracion
from mnemo.db.modelos import Base

motor = create_engine(obtener_configuracion().database_url)
FabricaSesiones = sessionmaker(bind=motor, expire_on_commit=False)


def crear_tablas(motor_=motor) -> None:
    Base.metadata.create_all(motor_)
