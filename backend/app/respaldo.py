"""
Respaldo de J.U.L.I.A.: base de datos + documentos. Igual en Mac y Windows.

    python -m app.respaldo            # respalda ahora
    python -m app.respaldo --si-falta # solo si hoy no se ha respaldado
                                      # (asi lo llama el arranque de la app)

Destino: la carpeta de respaldos de "Ajustes" (por defecto ~/Respaldos-JULIA):
  base_datos/dev002_AAAA-MM-DD_HHMM.sql.gz -> una copia por dia, se guardan
                                             las ultimas 60
  archivos/storage/, archivos/escritos_despacho/, archivos/J.U.L.I.A./
                                          -> espejo de los documentos; NUNCA
                                             borra nada del respaldo, aunque
                                             se borre en la app

Para tener copia fuera de la computadora, copiar esa carpeta a una USB de
vez en cuando.
"""

import glob
import gzip
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlmodel import Session

from app.carpetas import carpeta_archivos, carpeta_respaldos
from app.database import DATABASE_URL, engine

BASE_DIR = Path(__file__).resolve().parent.parent
CONSERVAR = 60


def _mysqldump() -> str:
    candidatos = [
        os.getenv("MYSQLDUMP"),
        shutil.which("mysqldump"),
        # MySQL que instala J.U.L.I.A. en Windows (junto al proyecto)
        str(BASE_DIR.parent / "mysql" / "bin" / "mysqldump.exe"),
        *sorted(glob.glob(r"C:\Program Files\MySQL\MySQL Server*\bin\mysqldump.exe")),
        *sorted(glob.glob("/Users/Shared/DBngin/mysql/*/bin/mysqldump")),  # Mac con DBngin
    ]
    for c in candidatos:
        if c and Path(c).exists():
            return c
    raise RuntimeError("No encontré mysqldump")


def _base_de_datos(destino: Path) -> Path:
    url = make_url(DATABASE_URL)
    archivo = destino / f"dev002_{datetime.now():%Y-%m-%d_%H%M}.sql.gz"
    tmp = archivo.with_name(archivo.name + ".tmp")
    cmd = [_mysqldump(), "-h", url.host or "127.0.0.1", "-P", str(url.port or 3306), "-u", url.username or "root",
           "--single-transaction", "--routines", "--no-tablespaces", "--set-gtid-purged=OFF", url.database or "dev002"]
    env = {**os.environ, "MYSQL_PWD": url.password or ""}  # sin poner la contrasena en la linea de comando
    with gzip.open(tmp, "wb") as salida:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)
        if proc.returncode != 0:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"mysqldump fallo: {proc.stderr.decode(errors='ignore').strip()}")
        salida.write(proc.stdout)
    tmp.replace(archivo)  # primero a un temporal: nunca queda un respaldo a medias
    return archivo


def _espejo(origen: Path, destino: Path) -> int:
    """Copia lo nuevo o cambiado; no borra nada del respaldo."""
    copiados = 0
    for f in origen.rglob("*"):
        if not f.is_file() or f.name.startswith(".julia_prueba"):
            continue
        d = destino / f.relative_to(origen)
        st = f.stat()
        if d.exists() and d.stat().st_size == st.st_size and d.stat().st_mtime >= st.st_mtime - 1:
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, d)
        copiados += 1
    return copiados


def respaldar(solo_si_falta: bool = False) -> str:
    with Session(engine) as session:
        destino, archivos = carpeta_respaldos(session), carpeta_archivos(session)
    bd = destino / "base_datos"
    hoy = f"dev002_{datetime.now():%Y-%m-%d}_"
    if solo_si_falta and bd.exists() and any(p.name.startswith(hoy) for p in bd.glob("*.sql.gz")):
        return "Ya hay respaldo de hoy"
    bd.mkdir(parents=True, exist_ok=True)

    # 1. Base de datos (clientes, servicios, casos, chats).
    archivo = _base_de_datos(bd)

    # 2. Documentos: los Word de los casos, los escritos viejos (storage/) y
    #    los escritos del despacho. Si la carpeta de archivos estuviera dentro
    #    de la de respaldos (o al reves), se salta para no copiarse a si misma.
    copias = 0
    for origen in (BASE_DIR / "storage", BASE_DIR / "escritos_despacho", archivos):
        if origen.is_dir() and not destino.is_relative_to(origen) and not origen.is_relative_to(destino):
            copias += _espejo(origen, destino / "archivos" / origen.name)
    if (BASE_DIR / ".env").exists():
        shutil.copy2(BASE_DIR / ".env", destino / "archivos" / ".env")

    # 3. Solo las ultimas CONSERVAR copias de la base.
    for viejo in sorted(bd.glob("dev002_*.sql.gz"), reverse=True)[CONSERVAR:]:
        viejo.unlink()

    return f"Respaldo listo: {archivo} ({copias} documentos nuevos o cambiados)"


if __name__ == "__main__":
    try:
        print(respaldar(solo_si_falta="--si-falta" in sys.argv))
    except Exception as e:
        print(f"Error en el respaldo: {e}", file=sys.stderr)
        sys.exit(1)
