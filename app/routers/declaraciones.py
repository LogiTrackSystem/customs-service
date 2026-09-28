from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DeclaracionAduanera
from ..schemas import DeclaracionAduaneraLeer, DeclaracionEstadoActualizar
from ..events import publish_event

router = APIRouter(prefix="/declaraciones", tags=["Declaraciones Aduaneras"])


@router.get("/", response_model=List[DeclaracionAduaneraLeer])
def listar_declaraciones(estado: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(DeclaracionAduanera)
    if estado:
        query = query.filter(DeclaracionAduanera.estado == estado)
    return query.order_by(DeclaracionAduanera.creado_en.desc()).all()


@router.get("/{envio_id}", response_model=DeclaracionAduaneraLeer)
def obtener_declaracion(envio_id: UUID, db: Session = Depends(get_db)):
    declaracion = (
        db.query(DeclaracionAduanera)
        .filter(DeclaracionAduanera.envio_id == envio_id)
        .first()
    )
    if declaracion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Declaración no encontrada")
    return declaracion


@router.patch("/{declaracion_id}/estado", response_model=DeclaracionAduaneraLeer)
async def actualizar_estado(declaracion_id: UUID, payload: DeclaracionEstadoActualizar, db: Session = Depends(get_db)):
    declaracion = db.query(DeclaracionAduanera).filter(DeclaracionAduanera.id == declaracion_id).first()
    if declaracion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Declaración no encontrada")

    declaracion.estado = payload.estado
    declaracion.motivo_retencion = payload.motivo_retencion
    db.commit()
    db.refresh(declaracion)

    routing_key = "customs.cleared" if payload.estado == "aprobado" else "customs.held"
    evento = {
        "declaracion_id": str(declaracion.id),
        "envio_id": str(declaracion.envio_id),
        "pais_origen": declaracion.pais_origen,
        "pais_destino": declaracion.pais_destino,
        "estado": declaracion.estado,
    }
    if declaracion.motivo_retencion:
        evento["motivo_retencion"] = declaracion.motivo_retencion
    await publish_event(routing_key, evento)

    return declaracion