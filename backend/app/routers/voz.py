"""
Asistente de voz (ver app/voz.py):

  POST /api/voz/transcribir?work_id=..   cuerpo: audio WAV -> {"texto": ...}
  POST /api/voz/hablar                   {"texto": ...}    -> audio/wav
  GET  /api/works/{id}/messages/{mid}/cambios  -> resumen de lo que cambio
  GET  /api/works/{id}/messages/{mid}/seccion?nombre=los hechos -> {"texto": ...}
  GET  /api/voz/estado
"""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app import voz
from app.cambios import extraer_seccion, resumir_cambios
from app.database import get_session
from app.models import Client, Service, Work, WorkMessage

router = APIRouter(tags=["voz"])

VOCABULARIO = (
    "apersonamiento, sucesorio intestamentario, causante, de cujus, presuntos herederos, albacea, "
    "promoción, demanda, contestación, alegatos, desahogo de vista, exhorto, emplazamiento, "
    "prestaciones, hechos, derecho, puntos petitorios, protesto lo necesario, proemio, rubro, "
    "Código Civil, Código de Procedimientos Civiles, artículo, fracción, expediente, juzgado, "
    "Tenango del Valle, Santiago Tianguistenco, Almoloya del Río, Estado de México, "
    "licenciada Juana Landa Hernández, Napoleón Ceballos Peña, Audelia Santiago Marcial, "
    # comandos de voz (frontend/src/lib/comandos.ts)
    "léeme los hechos, léeme todo, qué cambiaste, repite, envía la actualización, pásalo a Word"
)


def _pista_del_caso(session: Session, work_id: Optional[int]) -> str:
    """Nombres y terminos del caso para que Whisper los escriba bien."""
    partes = [VOCABULARIO]
    work = session.get(Work, work_id) if work_id else None
    if work:
        client = session.get(Client, work.client_id)
        service = session.get(Service, work.service_id)
        if client:
            partes.append(client.name)
        if service:
            partes.append(service.name)
        if work.notes:
            # nombres propios en MAYUSCULAS y numeros de expediente de las notas
            partes += re.findall(r"\b[A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{3,}){1,4}\b", work.notes)[:10]
            partes += re.findall(r"\b\d{1,5}/\d{2,4}\b", work.notes)[:3]
    return "Vocabulario: " + ", ".join(dict.fromkeys(partes)) + "."


@router.get("/voz/estado")
def estado_voz(precargar: bool = False):
    if precargar:
        voz.precargar()
    return voz.estado()


@router.post("/voz/transcribir")
async def transcribir(request: Request, work_id: Optional[int] = None, session: Session = Depends(get_session)):
    datos = await request.body()
    if not datos:
        raise HTTPException(status_code=400, detail="No llegó audio")
    pista = _pista_del_caso(session, work_id)
    try:
        texto = await run_in_threadpool(voz.transcribir, datos, pista)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"texto": texto}


class HablarIn(BaseModel):
    texto: str


@router.post("/voz/hablar")
async def hablar(payload: HablarIn):
    if not payload.texto.strip():
        raise HTTPException(status_code=400, detail="No hay texto que leer")
    audio = await run_in_threadpool(voz.hablar, payload.texto[:20000])
    return Response(content=audio, media_type="audio/wav")


@router.get("/works/{work_id}/messages/{message_id}/cambios")
def cambios(work_id: int, message_id: int, session: Session = Depends(get_session)):
    """Que cambio en este escrito respecto al escrito anterior del caso."""
    msg = session.get(WorkMessage, message_id)
    if not msg or msg.work_id != work_id or msg.role != "assistant":
        raise HTTPException(status_code=404, detail="Escrito no encontrado")
    if msg.tipo == "consulta":
        return {"resumen": msg.content}
    anterior = session.exec(
        select(WorkMessage)
        .where(WorkMessage.work_id == work_id, WorkMessage.role == "assistant",
               WorkMessage.tipo == "escrito", WorkMessage.id < message_id)
        .order_by(WorkMessage.id.desc())
    ).first()
    return {"resumen": resumir_cambios(anterior.content if anterior else None, msg.content)}


@router.get("/works/{work_id}/messages/{message_id}/seccion")
def seccion(work_id: int, message_id: int, nombre: str, session: Session = Depends(get_session)):
    """Una parte del escrito ("los hechos", "el derecho"...) para leerla en voz alta."""
    msg = session.get(WorkMessage, message_id)
    if not msg or msg.work_id != work_id or msg.role != "assistant":
        raise HTTPException(status_code=404, detail="Escrito no encontrado")
    return {"texto": extraer_seccion(msg.content, nombre)}
