import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .database import Base


class DeclaracionAduanera(Base):
    __tablename__ = "declaraciones_aduaneras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envio_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    pais_origen = Column(String, nullable=False)
    pais_destino = Column(String, nullable=False)
    documentos = Column(JSONB, nullable=False, default=list)
    estado = Column(String, nullable=False, default="pendiente")
    motivo_retencion = Column(String, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())