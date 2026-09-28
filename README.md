# Customs Service

Microservicio de documentación aduanera. Para envíos internacionales, consume `shipment.created` (publicado por Shipment Service), genera automáticamente la documentación requerida (factura comercial, certificado de origen, declaración aduanera) y valida el envío con reglas simples (países restringidos, inconsistencias de origen/destino), publicando `customs.cleared` o `customs.held` según el resultado.

## Requisitos

- Python 3.11+
- PostgreSQL
- RabbitMQ
- Shipment Service corriendo (para generar el evento `shipment.created` que dispara la creación de declaraciones)

## Setup

1. Crear la base de datos `customs_db`.
2. Copiar `.env.example` a `.env` y completar con tus credenciales reales.
3. `python -m venv venv && venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `alembic upgrade head`
6. `uvicorn app.main:app --reload --port 8006`

## Endpoints

- `GET /declaraciones/` — lista todas las declaraciones aduaneras (filtro opcional por `estado`).
- `GET /declaraciones/{envio_id}` — obtiene la declaración de un envío específico.
- `PATCH /declaraciones/{declaracion_id}/estado` — actualiza manualmente el estado (aprobado/retenido), útil para revisión humana.
- `GET /health` — healthcheck.

## Eventos

- **Consume:** `shipment.created` (solo procesa envíos con `es_internacional: true`)
- **Publica:** `customs.cleared`, `customs.held`