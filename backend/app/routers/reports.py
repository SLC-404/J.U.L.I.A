"""
Paso 8: reportes. Solo lo esencial: por cliente, cuantos casos (works) ha
tenido y cuanto suma lo acordado en ellos. Sin graficas ni filtros de fecha.

Nota: "total" es la suma de works.price (el precio ACORDADO de cada caso).
Todavia no registramos pagos, asi que no distingue lo cobrado de lo
pendiente.
"""

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import Client, Work

router = APIRouter(prefix="/reports", tags=["reports"])


class ClientReportRow(BaseModel):
    client_id: int
    name: str
    works_count: int
    total: float


@router.get("/clients", response_model=List[ClientReportRow])
def clients_report(session: Session = Depends(get_session)):
    # LEFT JOIN para que tambien salgan los clientes que aun no tienen casos.
    rows = session.exec(
        select(
            Client.id,
            Client.name,
            func.count(Work.id),
            func.coalesce(func.sum(Work.price), 0),
        )
        .join(Work, Work.client_id == Client.id, isouter=True)
        .group_by(Client.id, Client.name)
        .order_by(func.coalesce(func.sum(Work.price), 0).desc(), Client.name)
    ).all()

    return [
        ClientReportRow(client_id=cid, name=name, works_count=count, total=float(total))
        for cid, name, count, total in rows
    ]
