import json
import os
import uuid
import aio_pika
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import DeclaracionAduanera

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
EXCHANGE_NAME = "logitrack_events"

PAISES_RESTRINGIDOS = {"corea del norte", "iran", "siria", "cuba", "rusia"}

TIPOS_DOCUMENTOS = ["factura_comercial", "certificado_origen", "declaracion_aduanera"]


async def publish_event(routing_key: str, payload: dict):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        message = aio_pika.Message(
            body=json.dumps(payload, default=str).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=routing_key)


def _generar_documentos(envio_id: str) -> list[dict]:
    return [
        {"tipo": tipo, "url": f"https://docs.logitrack.local/aduanas/{envio_id}/{tipo}.pdf"}
        for tipo in TIPOS_DOCUMENTOS
    ]


def _evaluar_estado(pais_origen: str, pais_destino: str) -> tuple[str, str | None]:
    origen_norm = pais_origen.strip().lower()
    destino_norm = pais_destino.strip().lower()

    if origen_norm in PAISES_RESTRINGIDOS or destino_norm in PAISES_RESTRINGIDOS:
        return "retenido", "País de origen o destino sujeto a revisión aduanera obligatoria"

    if origen_norm == destino_norm:
        return "retenido", "El envío está marcado como internacional pero el país de origen y destino coinciden"

    return "aprobado", None


async def _procesar_shipment_created(payload: dict):
    if not payload.get("es_internacional"):
        return

    envio_id = uuid.UUID(payload["envio_id"])
    pais_origen = payload["origen"]
    pais_destino = payload["destino"]

    db: Session = SessionLocal()
    try:
        declaracion = (
            db.query(DeclaracionAduanera)
            .filter(DeclaracionAduanera.envio_id == envio_id)
            .first()
        )
        if declaracion:
            return  # ya existe una declaración para este envío

        estado, motivo = _evaluar_estado(pais_origen, pais_destino)

        declaracion = DeclaracionAduanera(
            envio_id=envio_id,
            pais_origen=pais_origen,
            pais_destino=pais_destino,
            documentos=_generar_documentos(str(envio_id)),
            estado=estado,
            motivo_retencion=motivo,
        )
        db.add(declaracion)
        db.commit()

        routing_key = "customs.cleared" if estado == "aprobado" else "customs.held"
        evento = {
            "declaracion_id": str(declaracion.id),
            "envio_id": str(envio_id),
            "pais_origen": pais_origen,
            "pais_destino": pais_destino,
            "estado": estado,
        }
        if motivo:
            evento["motivo_retencion"] = motivo
        await publish_event(routing_key, evento)
    finally:
        db.close()


async def _on_message(message: aio_pika.IncomingMessage):
    async with message.process():
        payload = json.loads(message.body.decode())
        await _procesar_shipment_created(payload)


async def iniciar_consumidor():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue("customs_service.shipment_created", durable=True)
    await queue.bind(exchange, routing_key="shipment.created")
    await queue.consume(_on_message)
    return connection