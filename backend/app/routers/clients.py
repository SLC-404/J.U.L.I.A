from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Client

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=List[Client])
def list_clients(session: Session = Depends(get_session)):
    return session.exec(select(Client)).all()


@router.post("/", response_model=Client)
def create_client(client: Client, session: Session = Depends(get_session)):
    client.id = None  # por si lo mandan por error, siempre se autogenera
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


@router.get("/{client_id}", response_model=Client)
def get_client(client_id: int, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.put("/{client_id}", response_model=Client)
def update_client(client_id: int, data: Client, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    updates = data.dict(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
    for key, value in updates.items():
        setattr(client, key, value)
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(client_id: int, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    session.delete(client)
    session.commit()
    return {"ok": True}
