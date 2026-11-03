"""Modelos de base de datos (SQLAlchemy 2)."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Estudiante(Base):
    __tablename__ = "estudiantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    respuestas: Mapped[list["Respuesta"]] = relationship(back_populates="estudiante")


class Curso(Base):
    __tablename__ = "cursos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    idioma_origen: Mapped[str] = mapped_column(String(10))
    idioma_destino: Mapped[str] = mapped_column(String(10))

    ejercicios: Mapped[list["Ejercicio"]] = relationship(back_populates="curso")


class Ejercicio(Base):
    __tablename__ = "ejercicios"

    id: Mapped[int] = mapped_column(primary_key=True)
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"))
    enunciado: Mapped[str] = mapped_column(Text)  # frase a traducir
    # Lista de traducciones válidas, p. ej. ["I am hungry", "I'm hungry"]
    soluciones: Mapped[list[str]] = mapped_column(JSON)

    curso: Mapped[Curso] = relationship(back_populates="ejercicios")


class Respuesta(Base):
    """Cada intento de un estudiante. En la Fase 2 se enviará también a ClickHouse."""

    __tablename__ = "respuestas"

    id: Mapped[int] = mapped_column(primary_key=True)
    estudiante_id: Mapped[int] = mapped_column(ForeignKey("estudiantes.id"))
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("ejercicios.id"))
    texto: Mapped[str] = mapped_column(Text)
    puntuacion: Mapped[float] = mapped_column(Float)
    veredicto: Mapped[str] = mapped_column(String(20))
    explicacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    estudiante: Mapped[Estudiante] = relationship(back_populates="respuestas")
    ejercicio: Mapped[Ejercicio] = relationship()
