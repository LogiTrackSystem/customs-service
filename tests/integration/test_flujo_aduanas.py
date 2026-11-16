"""Integración: evento de envío internacional -> declaración visible por API -> cambio de estado."""
import asyncio
import uuid

from app import events


def test_declaracion_retenida_se_consulta_y_se_aprueba_por_api(api, fabrica, monkeypatch):
    # Arrange: llega un envío hacia un país restringido
    monkeypatch.setattr(events, "SessionLocal", fabrica)
    envio_id = str(uuid.uuid4())
    asyncio.run(events._procesar_shipment_created(
        {"envio_id": envio_id, "es_internacional": True, "pais_origen": "Colombia", "pais_destino": "Cuba"}))
    # Act: se consulta por envío y luego se aprueba manualmente
    leida = api.get(f"/declaraciones/{envio_id}")
    cambio = api.patch(f"/declaraciones/{leida.json()['id']}/estado", json={"estado": "aprobado"})
    # Assert
    assert leida.status_code == 200 and leida.json()["estado"] == "retenido"
    assert cambio.status_code == 200 and cambio.json()["estado"] == "aprobado"
