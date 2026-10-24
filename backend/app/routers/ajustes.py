"""
Reglas del despacho: preferencias de redaccion de la Lic. Juana que el
asistente sigue SIEMPRE (pantalla "Reglas del despacho").

Vienen precargadas con lo que ella corrigio en el chat del caso de
María Pérez (oct 2026); ella las puede editar desde la app.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app import carpetas
from app.database import get_session
from app.models import Ajuste

router = APIRouter(prefix="/ajustes", tags=["ajustes"])

CLAVE_REGLAS = "reglas_despacho"

REGLAS_INICIALES = """\
1. En el cierre escribe solo "a usted C. Juez, atentamente pido:"; no repitas el nombre completo del juzgado (es relleno).
2. Nunca uses la expresión "auxilio jurisdiccional".
3. Si la persona es mujer, escribe "la suscrita", "notificada", "apersonada"; si es hombre, "el suscrito", "notificado", "apersonado".
4. En juicios sucesorios, el escrito para comparecer es un escrito de APERSONAMIENTO (no "promoción"). Petitorios: "PRIMERO.- Tener por presentado el presente escrito de apersonamiento." y "SEGUNDO.- Se tenga por autorizado el domicilio mencionado y a los profesionales en derecho citados."
5. Al apersonarse en un sucesorio NO menciones los bienes de la herencia (terrenos, casas): eso es de una etapa posterior.
6. En el proemio autoriza a los LICS. JUANA LANDA HERNÁNDEZ, NAPOLEÓN CEBALLOS PEÑA y AUDELIA SANTIAGO MARCIAL "para que reciban todo tipo de notificaciones, aun las de carácter personal".
7. Firma: después de "PROTESTO LO NECESARIO", el lugar y la fecha, el nombre del cliente y abajo "ABOGADO PATRONO / LIC. JUANA LANDA HERNÁNDEZ / CÉDULA PROFESIONAL NO. 3610993".
8. No escribas fechas que no vengan en las notas (por ejemplo, la de defunción). Nunca confundas la fecha en que notificaron al cliente con la fecha en que murió el autor de la herencia.
9. Para el expediente no uses "bajo la clave"; escribe "en el expediente número 123/2026" (con el número del caso).
10. Si piden "la fecha del próximo lunes" (u otro día), usa la fecha real de ese día.
11. En un apersonamiento, el hecho principal es la notificación: escribe en los HECHOS la fecha en que se notificó al cliente y que se le citó para apersonarse y justificar sus derechos.
"""


def leer_reglas(session: Session) -> str:
    ajuste = session.get(Ajuste, CLAVE_REGLAS)
    return ajuste.valor if ajuste else REGLAS_INICIALES


class ReglasIn(BaseModel):
    reglas: str


@router.get("/reglas")
def obtener_reglas(session: Session = Depends(get_session)):
    return {"reglas": leer_reglas(session)}


@router.put("/reglas")
def guardar_reglas(payload: ReglasIn, session: Session = Depends(get_session)):
    ajuste = session.get(Ajuste, CLAVE_REGLAS) or Ajuste(clave=CLAVE_REGLAS)
    ajuste.valor = payload.reglas.strip()
    session.add(ajuste)
    session.commit()
    return {"reglas": ajuste.valor}


# --- Carpetas (ver app/carpetas.py) --------------------------------------------


def _carpetas(session: Session) -> dict:
    archivos, respaldos = carpetas.carpeta_archivos(session), carpetas.carpeta_respaldos(session)
    defecto = carpetas.por_defecto()
    avisos = [
        f"La carpeta de {nombre} parece sincronizarse con la nube ({c}). Los datos de los clientes "
        "saldrían de la computadora; mejor elige una carpeta local."
        for nombre, c in (("archivos", archivos), ("respaldos", respaldos))
        if carpetas.en_la_nube(c)
    ]
    return {
        "archivos": str(archivos),
        "respaldos": str(respaldos),
        "por_defecto": {k: str(v) for k, v in defecto.items()},
        "avisos": avisos,
    }


class CarpetasIn(BaseModel):
    archivos: Optional[str] = None
    respaldos: Optional[str] = None


@router.get("/carpetas")
def obtener_carpetas(session: Session = Depends(get_session)):
    return _carpetas(session)


@router.put("/carpetas")
def guardar_carpetas(payload: CarpetasIn, session: Session = Depends(get_session)):
    try:
        if payload.archivos is not None:
            carpetas.guardar(session, carpetas.CLAVE_ARCHIVOS, carpetas.validar(payload.archivos))
        if payload.respaldos is not None:
            carpetas.guardar(session, carpetas.CLAVE_RESPALDOS, carpetas.validar(payload.respaldos))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    session.commit()
    return _carpetas(session)


class AbrirIn(BaseModel):
    cual: Literal["archivos", "respaldos"]


@router.post("/carpetas/abrir")
def abrir_carpeta(payload: AbrirIn, session: Session = Depends(get_session)):
    c = carpetas.carpeta_archivos(session) if payload.cual == "archivos" else carpetas.carpeta_respaldos(session)
    try:
        carpetas.abrir(c)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"No pude abrir la carpeta: {e}")
    return {"ok": True}
