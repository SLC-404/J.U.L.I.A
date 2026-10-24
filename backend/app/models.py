"""
Modelos de la base de datos (MySQL) usando SQLModel.

Cada clase aqui es a la vez:
  - un modelo de tabla (gracias a table=True)
  - un esquema de validacion de FastAPI (porque SQLModel hereda de Pydantic)

Asi evitamos duplicar la misma info en "modelo de base de datos" y
"esquema de la API" como se haria normalmente con SQLAlchemy + Pydantic
por separado.

Nota: los campos de texto libre (direcciones, notas, el contenido del
chat) usan Column(Text) en vez de dejarlos como str normal -- un str
normal en MySQL se crea como VARCHAR(255), que se queda corto rapido
(ej. una respuesta larga del agente no cabe ahi).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Text, func
from sqlmodel import Field, SQLModel


class Client(SQLModel, table=True):
    __tablename__ = "clients"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )


class Service(SQLModel, table=True):
    """Catalogo de servicios que ofrece el despacho (ej. 'Demanda de desahucio')."""

    __tablename__ = "services"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    status: str = Field(default="activo")

    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )


class Work(SQLModel, table=True):
    """
    Un 'work' es el caso/trabajo real que se le hizo a un cliente especifico.
    Aqui vive el precio REAL acordado (puede diferir del precio de lista
    en `services`), porque en la practica legal casi siempre se negocia.
    """

    __tablename__ = "works"

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="clients.id")
    service_id: int = Field(foreign_key="services.id")
    price: float
    status: str = Field(default="activo")
    started_at: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )


class WorkFile(SQLModel, table=True):
    """Un documento (generado por la IA o subido a mano) de un work especifico."""

    __tablename__ = "work_files"

    id: Optional[int] = Field(default=None, primary_key=True)
    work_id: int = Field(foreign_key="works.id")
    filename: str
    path: str
    type: str = Field(default="borrador_ia")  # borrador_ia | final | subido
    status: str = Field(default="borrador")

    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )


class WorkMessage(SQLModel, table=True):
    """Un mensaje del chat del agente, siempre amarrado a UN work (caso)."""

    __tablename__ = "work_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    work_id: int = Field(foreign_key="works.id")
    role: str  # "user" | "assistant"
    content: str = Field(sa_column=Column(Text))
    # "escrito" (se puede editar y exportar a Word) o "consulta" (respuesta a
    # una pregunta de la abogada).
    tipo: str = Field(default="escrito", max_length=20)

    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )


class Ajuste(SQLModel, table=True):
    """Configuracion del despacho guardada en la base (clave -> texto). Por
    ahora: "reglas_despacho", las preferencias de redaccion de la Lic. Juana
    que el asistente debe seguir siempre."""

    __tablename__ = "ajustes"

    clave: str = Field(primary_key=True, max_length=100)
    valor: str = Field(default="", sa_column=Column(Text))

    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )
