"""
Donde guarda J.U.L.I.A. los archivos (pantalla "Ajustes"). Se puede cambiar
desde la app; se guarda en la tabla `ajustes`.

- Archivos: los Word de cada caso, en <carpeta>/Casos/<Cliente>/<Servicio (caso N)>/
  con nombres legibles, para que la Lic. los encuentre en el Explorador.
  Por defecto ~/J.U.L.I.A. (en Windows C:\\Users\\<ella>\\J.U.L.I.A.).
- Respaldos: copia diaria de la base y de los documentos. Por defecto
  ~/Respaldos-JULIA (donde ya estaban en la Mac).

Ninguna va en Documentos por defecto: en Windows OneDrive suele subir
Documentos a la nube (y en la Mac, iCloud), y los datos de los clientes no
deben salir de la computadora. Si la Lic. elige una carpeta que se
sincroniza con la nube, la app le avisa.

Los archivos viejos (de antes de este ajuste) siguen en backend/storage/ y
se descargan igual.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from sqlmodel import Session

from app.models import Ajuste

CLAVE_ARCHIVOS = "carpeta_archivos"
CLAVE_RESPALDOS = "carpeta_respaldos"

_NUBE = ("OneDrive", "iCloud", "Mobile Documents", "CloudStorage", "Google Drive", "GoogleDrive", "Dropbox")


def por_defecto() -> dict[str, Path]:
    return {"archivos": Path.home() / "J.U.L.I.A.", "respaldos": Path.home() / "Respaldos-JULIA"}


def _leer(session: Session, clave: str, defecto: Path) -> Path:
    ajuste = session.get(Ajuste, clave)
    return Path(ajuste.valor) if ajuste and ajuste.valor else defecto


def carpeta_archivos(session: Session) -> Path:
    return _leer(session, CLAVE_ARCHIVOS, por_defecto()["archivos"])


def carpeta_respaldos(session: Session) -> Path:
    return _leer(session, CLAVE_RESPALDOS, por_defecto()["respaldos"])


def en_la_nube(carpeta: Path) -> bool:
    return any(n.lower() in str(carpeta).lower() for n in _NUBE)


def validar(texto: str) -> Path:
    """Ruta que escribio la Lic. -> carpeta lista para usar, o ValueError con
    un mensaje que ella entienda."""
    texto = texto.strip().strip('"')
    if not texto:
        raise ValueError("Escribe una ruta de carpeta.")
    carpeta = Path(os.path.expandvars(texto)).expanduser()
    if not carpeta.is_absolute():
        raise ValueError("Escribe la ruta completa, por ejemplo C:\\Users\\Juana\\J.U.L.I.A. o /Users/juana/J.U.L.I.A.")
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
        prueba = carpeta / ".julia_prueba"
        prueba.write_text("ok")
        prueba.unlink()
    except OSError as e:
        raise ValueError(f"No puedo guardar archivos en esa carpeta ({e.strerror or e}).")
    return carpeta


def guardar(session: Session, clave: str, carpeta: Path) -> None:
    ajuste = session.get(Ajuste, clave) or Ajuste(clave=clave)
    ajuste.valor = str(carpeta)
    session.add(ajuste)


def nombre_seguro(texto: str, largo: int = 80) -> str:
    """Nombre valido de carpeta/archivo en Windows y Mac, conservando acentos
    y mayusculas: 'Juicio: sucesorio/2026' -> 'Juicio sucesorio 2026'."""
    texto = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip().rstrip(". ")
    return texto[:largo].rstrip(". ") or "sin nombre"


def carpeta_del_caso(session: Session, client_name: str, work_id: int, service_name: str) -> Path:
    carpeta = (
        carpeta_archivos(session)
        / "Casos"
        / nombre_seguro(client_name)
        / f"{nombre_seguro(service_name, 60)} (caso {work_id})"
    )
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def abrir(carpeta: Path) -> None:
    """Abre la carpeta en el Explorador (Windows) o el Finder (Mac)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(carpeta)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(carpeta)])
    else:
        subprocess.Popen(["xdg-open", str(carpeta)])
