from contextlib import asynccontextmanager
from fastapi import FastAPI
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "customs-service"}