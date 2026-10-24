"""
Pantalla "Leyes": que version de cada codigo usa el asistente, y el boton
"Buscar actualizaciones" (ver app/leyes.py).
"""

from fastapi import APIRouter

from app import leyes

router = APIRouter(prefix="/leyes", tags=["leyes"])


@router.get("/")
def estado_de_las_leyes():
    versiones = leyes.leer_versiones()
    codigos = []
    for c in leyes.CODIGOS:
        info = versiones.get(c.archivo, {})
        codigos.append({
            "archivo": c.archivo,
            "nombre": c.nombre.split(" (")[0],
            "fuente": info.get("url") or c.url,
            "ultima_reforma": info.get("ultima_reforma"),
            "revisado": info.get("revisado"),
            "actualizado": info.get("actualizado"),
            "error": info.get("error"),
            "descargado": (leyes.LEGAL_CORPUS_DIR / c.archivo).exists(),
        })
    return {"codigos": codigos, "trabajo": leyes.estado, "programacion": leyes.leer_programacion()}


@router.post("/actualizar")
def buscar_actualizaciones():
    arrancado = leyes.iniciar_actualizacion()
    return {"arrancado": arrancado, "trabajo": leyes.estado}
