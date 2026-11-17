import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .interno import proteger_servicio

from .routers import declaraciones
from .events import iniciar_consumidor


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = await iniciar_consumidor()
    yield
    await connection.close()


app = FastAPI(title="Customs Service", lifespan=lifespan)
app.include_router(declaraciones.router)
proteger_servicio(app)


# Métricas para Prometheus (GET /metrics): peticiones por método/estado y tiempos de respuesta
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, include_in_schema=False)


@app.get("/health")
def health():
    return {"status": "ok", "service": "customs-service", "version": os.getenv("APP_VERSION", "dev")}