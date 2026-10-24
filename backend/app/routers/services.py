from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Service

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/", response_model=List[Service])
def list_services(session: Session = Depends(get_session)):
    return session.exec(select(Service)).all()


@router.post("/", response_model=Service)
def create_service(service: Service, session: Session = Depends(get_session)):
    service.id = None
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


@router.get("/{service_id}", response_model=Service)
def get_service(service_id: int, session: Session = Depends(get_session)):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return service


@router.put("/{service_id}", response_model=Service)
def update_service(service_id: int, data: Service, session: Session = Depends(get_session)):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    updates = data.dict(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
    for key, value in updates.items():
        setattr(service, key, value)
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


@router.delete("/{service_id}")
def delete_service(service_id: int, session: Session = Depends(get_session)):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    session.delete(service)
    session.commit()
    return {"ok": True}
