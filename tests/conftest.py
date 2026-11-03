"""Pruebas de Customs con SQLite en memoria (sin PostgreSQL ni RabbitMQ)."""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite://"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db
from app.main import app


@compiles(JSONB, "sqlite")  # SQLite no tiene JSONB: en las pruebas se guarda como JSON
def _jsonb_en_sqlite(tipo, compilador, **kw):
    return "JSON"


@pytest.fixture()
def fabrica():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture()
def db(fabrica):
    sesion = fabrica()
    yield sesion
    sesion.close()


@pytest.fixture()
def publicados(monkeypatch):
    """Sustituye la publicación a RabbitMQ y devuelve la lista de (clave, evento) 'publicados'."""
    from app import events
    from app.routers import declaraciones

    lista = []

    async def falso(clave, payload):
        lista.append((clave, payload))

    monkeypatch.setattr(events, "publish_event", falso)
    monkeypatch.setattr(declaraciones, "publish_event", falso)
    return lista


@pytest.fixture()
def api(fabrica, monkeypatch, publicados):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)  # un .env local no debe afectar a las pruebas

    def _get_db():
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = _get_db
    # sin 'with': no se ejecuta el arranque (conexión a RabbitMQ)
    yield TestClient(app)
    app.dependency_overrides.clear()
