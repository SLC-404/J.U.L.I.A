from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Work

router = APIRouter(prefix="/works", tags=["works"])


def _to_datetime(value):
    """Los modelos con table=True no validan al recibir el JSON, asi que
    started_at llega como texto ISO (ej. '2026-10-20T02:59:32.184Z').
    Lo convertimos a datetime con zona horaria (SQLModel la exige)."""
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
    return value


@router.get("/", response_model=List[Work])
def list_works(
    client_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    """Lista todos los works, o solo los de un cliente si mandas ?client_id=."""
    query = select(Work)
    if client_id is not None:
        query = query.where(Work.client_id == client_id)
    return session.exec(query).all()


@router.post("/", response_model=Work)
def create_work(work: Work, session: Session = Depends(get_session)):
    work.id = None
    work.started_at = _to_datetime(work.started_at) or datetime.now().astimezone()
    session.add(work)
    session.commit()
    session.refresh(work)
    return work


@router.get("/{work_id}", response_model=Work)
def get_work(work_id: int, session: Session = Depends(get_session)):
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return work


@router.put("/{work_id}", response_model=Work)
def update_work(work_id: int, data: Work, session: Session = Depends(get_session)):
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    updates = data.dict(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
    if "started_at" in updates:
        updates["started_at"] = _to_datetime(updates["started_at"])
    for key, value in updates.items():
        setattr(work, key, value)
    session.add(work)
    session.commit()
    session.refresh(work)
    return work


@router.delete("/{work_id}")
def delete_work(work_id: int, session: Session = Depends(get_session)):
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    session.delete(work)
    session.commit()
    return {"ok": True}
