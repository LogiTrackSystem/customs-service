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

---

<!-- entrega-final -->

## Descripción

Declaraciones aduaneras de los envíos internacionales: las aprueba o las retiene y permite cambiar su estado.

- **Puerto local:** 8006   ·   **Despliegue activo:** <https://logitrack-customs.onrender.com> (`/health` y `/metrics` públicos)
- **Imagen Docker:** `<usuario-dockerhub>/logitrack-customs`   ·   **Repositorio de CI/CD:** `LogiTrackSystem/pipelines`

## Variables de entorno

Copia `.env.example` como `.env` y completa los valores. El `.env` **no se sube** al repositorio.

| Variable | Para qué sirve |
|---|---|
| `DATABASE_URL` | Conexión a la base PostgreSQL del servicio (`postgresql://usuario:clave@host:5432/<base>`). Es un secreto. |
| `RABBITMQ_URL` | URL AMQP del bus de eventos RabbitMQ (CloudAMQP en producción). Es un secreto. |
| `INTERNAL_API_KEY` | Clave compartida entre el gateway y los servicios: exige la cabecera `X-Internal-Key` en todas las rutas salvo `/health` y `/metrics`. Vacía = sin restricción (solo local). Es un secreto. |

## Documentación de la API

- **Local** (sin `INTERNAL_API_KEY`): <http://localhost:8006/docs> (Swagger) y `http://localhost:8006/openapi.json`.
- **Producción:** el servicio solo atiende peticiones que llegan por el gateway (con `INTERNAL_API_KEY` activa su `/docs` no es público); la documentación de todas las rutas está en <https://logitrack-gateway.onrender.com/docs>.

## Base de datos

- Migraciones con Alembic (`alembic/`): `alembic upgrade head` (el `Dockerfile` ya lo ejecuta al arrancar).
- `db/esquema.sql`: esquema completo de `customs_db` generado desde las migraciones.
- Datos de ejemplo: este servicio se alimenta de eventos y llamadas de otros servicios; se generan ejecutando el flujo completo (por ejemplo `_pruebas/casos.py` del proyecto).
- Respaldo y restauración: ver `db/README.md`.

## Pruebas

Con el entorno virtual activo y `pip install -r requirements-dev.txt`:

```
pytest tests/unit                    # 2 pruebas unitarias
pytest tests/integration             # 1 prueba de integración
pytest --cov=app --cov-report=term   # toda la suite con cobertura
```

| Prueba | Qué verifica |
|---|---|
| Unitaria 1 | `events._evaluar_estado` |
| Unitaria 2 | `events._procesar_shipment_created` |
| Integración | evento de envío internacional → declaración → cambio de estado por API |

Archivos: `tests/unit/` y `tests/integration/` (test_evaluar_estado.py, test_envio_creado.py, test_flujo_aduanas.py). Cobertura de `app/` medida: **≈ 86 %**; en cada push y Pull Request GitHub Actions la recalcula y guarda `coverage.xml` como artefacto (`cobertura-customs`).

## Métricas y monitoreo

Expone `GET /metrics` (formato Prometheus: `http_requests_total` y `http_request_duration_*`). Prometheus y el dashboard de Grafana están en el repositorio `logitrack-monitoring`.

## CI/CD

- `.github/workflows/pr.yml`: en cada push (rama distinta de `main`) y en cada Pull Request a `main` ejecuta el CI reutilizable (lint, pruebas con cobertura, `docker build` y prueba de arranque).
- `.github/workflows/deploy.yml`: al fusionar en `main`, y solo con las pruebas en verde, publica la imagen en Docker Hub y despliega en Render (con verificación de `/health` y rollback manual).
- Detalle y estrategia de ramas: `CICD.md` en el repositorio `LogiTrackSystem/pipelines`.

