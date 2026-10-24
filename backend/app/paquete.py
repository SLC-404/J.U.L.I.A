"""
Paquete de datos: para pasar J.U.L.I.A. de una computadora a otra (la Mac de
Cesar -> la laptop de Windows de la Lic.) sin empezar de cero.

    python -m app.paquete exportar [archivo.zip]
    python -m app.paquete importar archivo.zip [--reemplazar]

El .zip lleva: la base de datos (clientes, casos, chats, reglas), los Word
de los casos, los escritos del despacho, el indice del RAG (chroma_db) y la
voz de J.U.L.I.A. NO lleva modelos ni codigo (esos los baja el instalador).

TRAE DATOS DE CLIENTES: pasarlo por USB y borrarlo al terminar. Nunca
subirlo a internet.

Al importar, las rutas de la otra computadora (p. ej. /Users/cesar/J.U.L.I.A.)
se cambian por las de esta, y las carpetas de Ajustes vuelven a las de por
defecto de esta computadora.
"""

import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine, select

from app import carpetas
from app.database import DATABASE_URL, engine
from app.models import Ajuste, WorkFile
from app.respaldo import _base_de_datos, buscar_mysql

BASE_DIR = Path(__file__).resolve().parent.parent
VERSION = 1
# carpetas de backend/ que viajan en el paquete
CARPETAS = ["storage", "escritos_despacho", "chroma_db"]
VOZ = Path("modelos_voz") / "voz_julia.wav"


# --- Exportar ----------------------------------------------------------------------

def _agregar(z: zipfile.ZipFile, origen: Path, destino: str) -> int:
    n = 0
    for f in sorted(origen.rglob("*")):
        if f.is_file() and f.name not in (".DS_Store", ".julia_prueba"):
            z.write(f, f"{destino}/{f.relative_to(origen).as_posix()}")
            n += 1
    return n


def exportar(salida: Path | None = None) -> Path:
    with Session(engine) as session:
        archivos = carpetas.carpeta_archivos(session)
        respaldos = carpetas.carpeta_respaldos(session)
    salida = salida or Path.home() / f"JULIA-paquete-{datetime.now():%Y-%m-%d_%H%M}.zip"
    manifiesto = {
        "version": VERSION,
        "creado": datetime.now().isoformat(timespec="seconds"),
        "origen": {"plataforma": sys.platform, "backend": str(BASE_DIR),
                   "carpeta_archivos": str(archivos), "carpeta_respaldos": str(respaldos)},
        "contenido": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        dump = _base_de_datos(Path(tmp))
        with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(dump, "base_datos.sql.gz")
            for nombre in CARPETAS:
                if (BASE_DIR / nombre).is_dir():
                    manifiesto["contenido"][nombre] = _agregar(z, BASE_DIR / nombre, nombre)
            if archivos.is_dir():
                manifiesto["contenido"]["archivos"] = _agregar(z, archivos, "archivos")
            if (BASE_DIR / VOZ).exists():
                z.write(BASE_DIR / VOZ, VOZ.as_posix())
            z.writestr("manifiesto.json", json.dumps(manifiesto, ensure_ascii=False, indent=2))
    return salida


# --- Importar ----------------------------------------------------------------------

def _extraer(zip_path: Path, destino: Path) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        if "manifiesto.json" not in z.namelist():
            raise ValueError("Ese archivo no es un paquete de J.U.L.I.A. (no trae manifiesto.json).")
        for nombre in z.namelist():  # que ningun archivo se salga de la carpeta temporal
            if not (destino / nombre).resolve().is_relative_to(destino.resolve()):
                raise ValueError(f"Paquete dañado o sospechoso: {nombre}")
        z.extractall(destino)
    manifiesto = json.loads((destino / "manifiesto.json").read_text(encoding="utf-8"))
    if manifiesto.get("version") != VERSION:
        raise ValueError("El paquete es de otra versión de J.U.L.I.A.")
    return manifiesto


def _hay_datos() -> bool:
    try:
        with engine.connect() as c:
            return bool(c.execute(text("SELECT COUNT(*) FROM clients")).scalar())
    except Exception:
        return False  # no existe la base o la tabla todavia


def _restaurar_bd(dump_gz: Path) -> None:
    url = make_url(DATABASE_URL)
    # la base puede no existir todavia (instalacion nueva)
    servidor = create_engine(url.set(database=""))
    with servidor.begin() as c:
        c.execute(text(f"CREATE DATABASE IF NOT EXISTS `{url.database}` CHARACTER SET utf8mb4"))
    servidor.dispose()
    cmd = [buscar_mysql("mysql"), "-h", url.host or "127.0.0.1", "-P", str(url.port or 3306),
           "-u", url.username or "root", "--default-character-set=utf8mb4", url.database]
    env = {**os.environ, "MYSQL_PWD": url.password or ""}
    # (stdin=gzip.open(...) no sirve: subprocess le pasaria los bytes comprimidos)
    sql = gzip.decompress(dump_gz.read_bytes())
    proc = subprocess.run(cmd, input=sql, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"No se pudo cargar la base: {proc.stderr.decode(errors='ignore').strip()}")


def _copiar(origen: Path, destino: Path, reemplazar: bool) -> None:
    if destino.exists() and reemplazar:
        # lo de antes no se borra: se aparta con la fecha
        destino.rename(destino.with_name(f"{destino.name}.antes-{datetime.now():%Y%m%d-%H%M%S}"))
    shutil.copytree(origen, destino, dirs_exist_ok=True)


def nueva_ruta(ruta: str, origen: dict, carpeta_archivos: Path) -> str:
    """Ruta de un archivo guardada en la otra computadora -> ruta en esta.
    Las relativas (storage/...) no cambian."""
    def bajo(base: str) -> str | None:
        b = base.rstrip("/\\")
        if b and (ruta.startswith(b + "/") or ruta.startswith(b + "\\")):
            return ruta[len(b) + 1:].replace("\\", "/")
        return None

    if (rel := bajo(origen.get("carpeta_archivos", ""))) is not None:
        return str(carpeta_archivos.joinpath(*rel.split("/")))
    if (rel := bajo(origen.get("backend", ""))) is not None:
        return rel  # relativa a backend/, como las de antes
    return ruta


def importar(zip_path: Path, reemplazar: bool = False) -> str:
    if _hay_datos() and not reemplazar:
        raise RuntimeError("Esta computadora ya tiene clientes en J.U.L.I.A. Para encimar el paquete "
                           "usa --reemplazar (lo de antes se aparta, no se borra).")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        manifiesto = _extraer(zip_path, tmp)
        _restaurar_bd(tmp / "base_datos.sql.gz")

        for nombre in CARPETAS:
            if (tmp / nombre).is_dir():
                _copiar(tmp / nombre, BASE_DIR / nombre, reemplazar)
        if (tmp / VOZ).exists():
            (BASE_DIR / VOZ).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tmp / VOZ, BASE_DIR / VOZ)

        with Session(engine) as session:
            # Las carpetas de la otra computadora no existen aqui: por defecto.
            for clave in (carpetas.CLAVE_ARCHIVOS, carpetas.CLAVE_RESPALDOS):
                if (a := session.get(Ajuste, clave)) is not None:
                    session.delete(a)
            session.commit()
            destino_archivos = carpetas.carpeta_archivos(session)
            if (tmp / "archivos").is_dir():
                shutil.copytree(tmp / "archivos", destino_archivos, dirs_exist_ok=True)
            cambiados = 0
            for wf in session.exec(select(WorkFile)).all():
                nueva = nueva_ruta(wf.path, manifiesto["origen"], destino_archivos)
                if nueva != wf.path:
                    wf.path = nueva
                    session.add(wf)
                    cambiados += 1
            session.commit()

    c = manifiesto["contenido"]
    return (f"Paquete del {manifiesto['creado']} importado: {c.get('archivos', 0)} Word de casos, "
            f"{c.get('escritos_despacho', 0)} escritos del despacho, {c.get('storage', 0)} archivos viejos; "
            f"{cambiados} rutas actualizadas. Archivos en {destino_archivos}.")


if __name__ == "__main__":
    args = sys.argv[1:]
    try:
        if args[:1] == ["exportar"]:
            ruta = exportar(Path(args[1]) if len(args) > 1 else None)
            print(f"Paquete listo: {ruta}\nTRAE DATOS DE CLIENTES: pásalo por USB y bórralo al terminar.")
        elif args[:1] == ["importar"] and len(args) > 1:
            print(importar(Path(args[1]), reemplazar="--reemplazar" in args))
        else:
            print(__doc__)
            sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
