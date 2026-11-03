"""Reglas aduaneras: declaración automática al crearse un envío internacional y cambios de estado."""
import asyncio
import uuid

import pytest

from app import events
from app.models import DeclaracionAduanera


@pytest.fixture()
def entorno(fabrica, monkeypatch, publicados):
    monkeypatch.setattr(events, "SessionLocal", fabrica)
    return publicados


def crear_envio(**campos):
    envio_id = campos.pop("envio_id", None) or str(uuid.uuid4())
    payload = {"envio_id": envio_id, "es_internacional": True, "pais_origen": "Colombia", "pais_destino": "Ecuador", **campos}
    asyncio.run(events._procesar_shipment_created(payload))
    return envio_id


# ---------- evaluación de países ----------

def test_ruta_normal_se_aprueba():
    assert events._evaluar_estado("Colombia", "Ecuador") == ("aprobado", None)


@pytest.mark.parametrize("pais", ["Cuba", "  IRAN ", "siria", "Rusia", "Corea del Norte"])
def test_pais_restringido_se_retiene_sin_importar_mayusculas_ni_espacios(pais):
    estado, motivo = events._evaluar_estado("Colombia", pais)
    assert estado == "retenido" and "revisión aduanera" in motivo
    assert events._evaluar_estado(pais, "Colombia")[0] == "retenido"


def test_origen_y_destino_iguales_en_un_envio_internacional_se_retiene():
    estado, motivo = events._evaluar_estado("Colombia", " colombia ")
    assert estado == "retenido" and "coinciden" in motivo


def test_se_generan_los_tres_documentos_con_el_envio_en_la_url():
    docs = events._generar_documentos("abc")
    assert [d["tipo"] for d in docs] == ["factura_comercial", "certificado_origen", "declaracion_aduanera"]
    assert all("/abc/" in d["url"] for d in docs)


# ---------- consumo de shipment.created ----------

def test_envio_internacional_aprobado_crea_declaracion_y_publica_cleared(entorno, db):
    envio_id = crear_envio()
    dec = db.query(DeclaracionAduanera).one()
    assert str(dec.envio_id) == envio_id and dec.estado == "aprobado" and dec.motivo_retencion is None
    assert len(dec.documentos) == 3
    clave, evento = entorno[0]
    assert clave == "customs.cleared" and evento["envio_id"] == envio_id and "motivo_retencion" not in evento


def test_envio_a_pais_restringido_queda_retenido_y_publica_held(entorno, db):
    crear_envio(pais_destino="Cuba")
    dec = db.query(DeclaracionAduanera).one()
    assert dec.estado == "retenido" and dec.motivo_retencion
    clave, evento = entorno[0]
    assert clave == "customs.held" and evento["motivo_retencion"] == dec.motivo_retencion


def test_envio_nacional_no_genera_declaracion(entorno, db):
    crear_envio(es_internacional=False)
    assert db.query(DeclaracionAduanera).count() == 0 and entorno == []


def test_el_mismo_envio_no_se_declara_dos_veces(entorno, db):
    envio_id = crear_envio()
    crear_envio(envio_id=envio_id)
    assert db.query(DeclaracionAduanera).count() == 1 and len(entorno) == 1


def test_usa_origen_y_destino_si_no_vienen_los_paises(entorno, db):
    asyncio.run(events._procesar_shipment_created(
        {"envio_id": str(uuid.uuid4()), "es_internacional": True, "origen": "Colombia", "destino": "Peru"}))
    dec = db.query(DeclaracionAduanera).one()
    assert (dec.pais_origen, dec.pais_destino) == ("Colombia", "Peru")


# ---------- API ----------

def test_obtener_y_listar_declaraciones(api, entorno, db):
    envio_id = crear_envio()
    crear_envio(pais_destino="Rusia")
    assert api.get(f"/declaraciones/{envio_id}").json()["estado"] == "aprobado"
    assert len(api.get("/declaraciones/").json()) == 2
    assert [d["estado"] for d in api.get("/declaraciones/?estado=retenido").json()] == ["retenido"]


def test_declaracion_inexistente_da_404(api):
    assert api.get(f"/declaraciones/{uuid.uuid4()}").status_code == 404
    assert api.get("/declaraciones/no-es-uuid").status_code == 422


def test_aprobar_una_declaracion_retenida_publica_cleared(api, entorno, db):
    crear_envio(pais_destino="Cuba")
    entorno.clear()
    dec = db.query(DeclaracionAduanera).one()
    r = api.patch(f"/declaraciones/{dec.id}/estado", json={"estado": "aprobado"})
    assert r.status_code == 200 and r.json()["estado"] == "aprobado" and r.json()["motivo_retencion"] is None
    assert entorno[0][0] == "customs.cleared"


def test_retener_una_declaracion_publica_held_con_motivo(api, entorno, db):
    crear_envio()
    entorno.clear()
    dec = db.query(DeclaracionAduanera).one()
    r = api.patch(f"/declaraciones/{dec.id}/estado", json={"estado": "retenido", "motivo_retencion": "Falta factura"})
    assert r.status_code == 200
    clave, evento = entorno[0]
    assert clave == "customs.held" and evento["motivo_retencion"] == "Falta factura"


def test_cambiar_estado_de_una_declaracion_inexistente_da_404_y_no_publica(api, entorno):
    r = api.patch(f"/declaraciones/{uuid.uuid4()}/estado", json={"estado": "aprobado"})
    assert r.status_code == 404 and entorno == []


def test_cambiar_estado_sin_estado_da_422(api, entorno, db):
    crear_envio()
    dec = db.query(DeclaracionAduanera).one()
    assert api.patch(f"/declaraciones/{dec.id}/estado", json={}).status_code == 422
