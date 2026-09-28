import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict


class DeclaracionAduaneraLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    envio_id: uuid.UUID
    pais_origen: str
    pais_destino: str
    documentos: List[Dict[str, str]]
    estado: str
    motivo_retencion: Optional[str] = None
    creado_en: datetime
    actualizado_en: datetime


class DeclaracionEstadoActualizar(BaseModel):
    estado: str
    motivo_retencion: Optional[str] = None