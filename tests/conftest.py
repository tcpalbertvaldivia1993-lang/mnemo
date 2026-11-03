"""Fixtures comunes: base de datos SQLite en memoria (no hace falta Docker para los tests)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from mnemo.db.modelos import Base
from mnemo.db.semilla import cargar_semilla


@pytest.fixture
def fabrica_sesiones():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(motor)
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    with fabrica() as sesion:
        cargar_semilla(sesion)
    return fabrica
