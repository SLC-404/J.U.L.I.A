"""
Conexion a MySQL. Lee la URL desde el archivo .env (ver .env.example).
"""

import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://root:password@127.0.0.1:3306/dev002"
)

# echo=True imprime cada SQL que se ejecuta -- util mientras aprendes,
# luego lo puedes poner en False.
engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """Crea las tablas que falten. No borra ni modifica las que ya existen."""
    # Se importan aqui (no arriba) para evitar import circular con los routers.
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _columnas_nuevas()


def _columnas_nuevas() -> None:
    """create_all no agrega columnas a tablas que ya existen; las que se
    fueron sumando despues se agregan aqui (una sola vez)."""
    from sqlalchemy import inspect, text

    columnas = {c["name"] for c in inspect(engine).get_columns("work_messages")}
    if "tipo" not in columnas:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE work_messages ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'escrito'"))


def get_session():
    """Dependencia de FastAPI: abre una sesion de DB por cada request."""
    with Session(engine) as session:
        yield session
