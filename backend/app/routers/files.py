"""
Paso 6: documentos de un caso (work_files).

Flujo: la usuaria platica con el agente en el chat del caso; cuando una
respuesta ya es el escrito que quiere, la exporta a Word con
POST /works/{work_id}/files/from-message/{message_id}. Eso genera el .docx
en la carpeta de archivos (Ajustes; ver app/carpetas.py), guarda la fila en work_files (type="borrador_ia") y se puede
descargar despues con GET /files/{file_id}/download.
"""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.aprendizaje import aprender, fue_editado_a_mano
from app.carpetas import carpeta_del_caso, nombre_seguro
from app.database import get_session
from app.docx_export import BASE_DIR, markdown_to_docx
from app.models import Client, Service, Work, WorkFile, WorkMessage

router = APIRouter(tags=["files"])

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class ExportIn(BaseModel):
    filename: Optional[str] = None  # sin extension; si no se manda, se arma solo


@router.get("/works/{work_id}/files", response_model=List[WorkFile])
def list_files(work_id: int, session: Session = Depends(get_session)):
    if not session.get(Work, work_id):
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return session.exec(
        select(WorkFile)
        .where(WorkFile.work_id == work_id)
        .order_by(WorkFile.created_at.desc())
    ).all()


@router.post(
    "/works/{work_id}/files/from-message/{message_id}", response_model=WorkFile
)
def export_message_to_docx(
    work_id: int,
    message_id: int,
    payload: Optional[ExportIn] = None,
    session: Session = Depends(get_session),
):
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    message = session.get(WorkMessage, message_id)
    if not message or message.work_id != work_id:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado en este caso")
    if message.role != "assistant":
        raise HTTPException(
            status_code=400, detail="Solo se pueden exportar respuestas del agente"
        )

    client = session.get(Client, work.client_id)
    service = session.get(Service, work.service_id)
    client_name = client.name if client else "cliente"
    service_name = service.name if service else "caso"

    # Nombres legibles para la Lic. en el Explorador:
    # "Juicio sucesorio intestamentario 2026-10-24 1430.docx"
    base = payload.filename if payload and payload.filename else service_name
    filename = f"{nombre_seguro(base, 70)} {datetime.now():%Y-%m-%d %H%M}.docx"

    dest = carpeta_del_caso(session, client_name, work.id, service_name) / filename
    markdown_to_docx(message.content, dest)

    # Si la Lic. lo corrigio a mano, es una version revisada por ella: se marca
    # como final y el asistente la aprende como modelo (app/aprendizaje.py).
    revisado = message.tipo == "escrito" and fue_editado_a_mano(message.created_at, message.updated_at)
    if revisado:
        try:
            aprender(dest, message.content, client_name, service_name, message.id)
        except Exception as e:  # aprender nunca debe impedir exportar
            print(f"[aprendizaje] no se pudo aprender del mensaje {message.id}: {e}")

    work_file = WorkFile(
        work_id=work_id,
        filename=filename,
        # Ruta completa (la carpeta de archivos puede estar en cualquier lado).
        path=str(dest),
        type="revisado_lic" if revisado else "borrador_ia",
        status="final" if revisado else "borrador",
    )
    session.add(work_file)
    session.commit()
    session.refresh(work_file)
    return work_file


@router.get("/files/{file_id}/download")
def download_file(file_id: int, session: Session = Depends(get_session)):
    work_file = session.get(WorkFile, file_id)
    if not work_file:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Los archivos viejos guardaron la ruta relativa a backend/ (storage/...).
    path = Path(work_file.path)
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="El archivo ya no esta en disco")

    # Los escritos importados pueden ser .docx, .doc viejo o PDF.
    media_type = mimetypes.guess_type(work_file.filename)[0] or DOCX_MEDIA_TYPE
    return FileResponse(path, media_type=media_type, filename=work_file.filename)
