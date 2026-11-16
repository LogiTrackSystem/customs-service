"""Unitaria 2: events._procesar_shipment_created crea la declaración y publica el evento."""
import asyncio
import uuid

from app import events
from app.models import DeclaracionAduanera


def test_envio_internacional_crea_declaracion_y_publica_evento(db, fabrica, publicados, monkeypatch):
    # Arrange: la función abre su propia sesión; se apunta a la base en memoria
    monkeypatch.setattr(events, "SessionLocal", fabrica)
    envio_id = str(uuid.uuid4())
    payload = {"envio_id": envio_id, "es_internacional": True, "pais_origen": "Colombia", "pais_destino": "Ecuador"}
    # Act
    asyncio.run(events._procesar_shipment_created(payload))
    # Assert
    declaracion = db.query(DeclaracionAduanera).one()
    assert declaracion.estado == "aprobado"
    assert publicados[0][0] == "customs.cleared"
