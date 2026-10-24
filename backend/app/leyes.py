"""
Actualizacion de los codigos legales que usa el asistente (RAG, coleccion
"leyes" de Chroma).

"Buscar actualizaciones" (boton en la pantalla Leyes) hace, para cada codigo:
  1. Baja el PDF de su fuente oficial.
  2. Confirma por el titulo que sea el codigo correcto (si el sitio cambio la
     numeracion de sus archivos, lo busca entre los demas).
  3. Lo compara con el que ya tenemos (huella del archivo). Si es igual, no
     hace nada.
  4. Si cambio: reemplaza el PDF en legal_corpus/ y vuelve a indexar SOLO ese
     codigo (borra sus fragmentos viejos de Chroma y mete los nuevos).

Lo que se sabe de cada codigo (fecha de ultima reforma, cuando se reviso y
actualizo) queda en legal_corpus/versiones.json.

Solo se conecta a internet para bajar leyes publicas; ningun dato de clientes
sale de la computadora.
"""

import hashlib
import json
import os
import re
import ssl
import tempfile
import threading
import unicodedata
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

import certifi
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
LEGAL_CORPUS_DIR = BASE_DIR / "legal_corpus"
CHROMA_DIR = BASE_DIR / "chroma_db"
VERSIONES = LEGAL_CORPUS_DIR / "versiones.json"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

_EDOMEX = "https://legislacion.edomex.gob.mx/sites/legislacion.edomex.gob.mx/files/files/pdf/cod/vig/codvig{:03d}.pdf"


@dataclass(frozen=True)
class Codigo:
    archivo: str  # nombre del PDF en legal_corpus/ (y clave en Chroma)
    nombre: str  # como lo cita el asistente
    url: str  # fuente oficial
    titulo: str  # lo que debe decir la portada (para confirmar que es el correcto)
    buscar_en_edomex: bool = False  # si el numero de archivo cambio, buscarlo


CODIGOS = [
    Codigo(
        archivo="codigo_civil_edomex.pdf",
        nombre="Código Civil del Estado de México",
        url=_EDOMEX.format(1),
        titulo="codigo civil del estado de mexico",
        buscar_en_edomex=True,
    ),
    Codigo(
        archivo="codigo_procedimientos_civiles_edomex.pdf",
        nombre=(
            "Código de Procedimientos Civiles del Estado de México (el anterior; "
            "sigue vigente en lo que se completa la transición al código nacional)"
        ),
        url=_EDOMEX.format(3),
        titulo="codigo de procedimientos civiles del estado de mexico",
        buscar_en_edomex=True,
    ),
    Codigo(
        archivo="codigo_nacional_procedimientos_civiles_familiares.pdf",
        nombre=(
            "Código Nacional de Procedimientos Civiles y Familiares (el nuevo, "
            "va reemplazando poco a poco a los códigos de procedimientos estatales)"
        ),
        url="https://www.diputados.gob.mx/LeyesBiblio/pdf/CNPCF.pdf",
        titulo="codigo nacional de procedimientos civiles y familiares",
    ),
]

_REFORMA = re.compile(
    r"[ÚU]ltima\s+reforma[^0-9]{0,25}(\d{1,2}\s+de\s+[a-záéíóú]+\s+de\s+\d{4}|\d{2}-\d{2}-\d{4})",
    re.I,
)


def _clave(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def _portada(path: Path) -> str:
    reader = PdfReader(str(path))
    return " ".join((reader.pages[i].extract_text() or "") for i in range(min(2, len(reader.pages))))


def ultima_reforma(path: Path) -> Optional[str]:
    """'16 de junio de 2026' o '15-01-2026', tal como viene en la portada."""
    m = _REFORMA.search(" ".join(_portada(path).split()))
    return m.group(1) if m else None


def _huella(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


# El Python de python.org en Mac no trae los certificados raiz y todo HTTPS
# fallaba con CERTIFICATE_VERIFY_FAILED; certifi trae la lista actualizada.
_SSL = ssl.create_default_context(cafile=certifi.where())


class SinRespuesta(Exception):
    """El sitio oficial no respondio (lento, caido o sin internet)."""


def _bajar(url: str, destino: Path, intentos: int = 2) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (J.U.L.I.A. despacho Lic. Landa)"})
    for intento in range(1, intentos + 1):
        try:
            # timeout = segundos maximos sin recibir nada (no el total)
            with urllib.request.urlopen(req, timeout=45, context=_SSL) as resp, open(destino, "wb") as f:
                while bloque := resp.read(1 << 20):
                    f.write(bloque)
            break
        except (TimeoutError, OSError) as e:  # URLError y timeouts heredan de OSError
            if intento == intentos:
                raise SinRespuesta(
                    "El sitio oficial no respondió (puede estar lento o no hay internet)"
                ) from e
    with open(destino, "rb") as f:
        if f.read(5) != b"%PDF-":
            raise ValueError("lo que se bajó no es un PDF")


def _es_el_codigo(path: Path, codigo: Codigo) -> bool:
    return codigo.titulo in _clave(_portada(path))[:600]


def leer_versiones() -> dict:
    if VERSIONES.exists():
        return json.loads(VERSIONES.read_text(encoding="utf-8"))
    return {}


def _guardar_versiones(v: dict) -> None:
    VERSIONES.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")


BIBLIOTECA_DIR = LEGAL_CORPUS_DIR / "articulos"


def indexar_codigo(codigo: Codigo, reforma: Optional[str]) -> int:
    """Separa el PDF en ARTICULOS (ver app/articulos.py), guarda la biblioteca
    del codigo (legal_corpus/articulos/<codigo>.json) y mete a Chroma un
    fragmento por articulo vigente, con su numero, epigrafe y ubicacion.
    Borra antes lo que hubiera de ese codigo. Regresa cuantos articulos quedaron."""
    import chromadb
    from llama_index.core import Settings, StorageContext, VectorStoreIndex
    from llama_index.core.schema import TextNode
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore

    from app.articulos import guardar_biblioteca, separar_articulos

    articulos = separar_articulos(LEGAL_CORPUS_DIR / codigo.archivo)
    if len(articulos) < 50:
        raise ValueError(f"solo se encontraron {len(articulos)} articulos; el PDF no tiene el formato esperado")
    guardar_biblioteca(codigo.archivo, articulos, BIBLIOTECA_DIR)

    Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text", base_url=OLLAMA_HOST)
    collection = chromadb.PersistentClient(path=str(CHROMA_DIR)).get_or_create_collection("leyes")
    collection.delete(where={"archivo": codigo.archivo})

    nodos = []
    for a in articulos:
        if a.derogado:
            continue
        encabezado = f"Artículo {a.articulo}" + (f". {a.epigrafe}" if a.epigrafe else "")
        nodo = TextNode(
            # El texto que se busca y que ve el modelo: numero + epigrafe +
            # donde vive + el articulo completo.
            text=f"{encabezado}\n({a.ubicacion})\n{a.texto}",
            metadata={
                "codigo": codigo.nombre,
                "archivo": codigo.archivo,
                "articulo": a.articulo,
                "epigrafe": a.epigrafe,
                "ubicacion": a.ubicacion,
                "ultima_reforma": reforma or "sin fecha",
            },
        )
        nodo.excluded_embed_metadata_keys = list(nodo.metadata)
        nodo.excluded_llm_metadata_keys = list(nodo.metadata)
        nodos.append(nodo)

    VectorStoreIndex(
        nodos,
        storage_context=StorageContext.from_defaults(
            vector_store=ChromaVectorStore(chroma_collection=collection)
        ),
        show_progress=False,
    )
    return len(nodos)


def _buscar_en_edomex(codigo: Codigo, tmp: Path, avisar: Callable[[str], None]) -> Optional[str]:
    """El sitio del Edomex numera sus codigos (codvig001, codvig002...). Si el
    numero cambio, revisa los primeros 30 hasta dar con el del titulo."""
    for n in range(1, 31):
        url = _EDOMEX.format(n)
        if url == codigo.url:
            continue
        avisar(f"Buscando el {codigo.nombre.split(' (')[0]} en el sitio del Edomex ({n}/30)…")
        try:
            _bajar(url, tmp)
            if _es_el_codigo(tmp, codigo):
                return url
        except Exception:
            continue
    return None


def revisar_y_actualizar(avisar: Callable[[str], None]) -> list[dict]:
    """Revisa cada codigo contra su fuente oficial y actualiza los que
    cambiaron. `avisar` recibe mensajes de progreso para la pantalla."""
    versiones = leer_versiones()
    resultados = []
    ahora = datetime.now().isoformat(timespec="seconds")

    for codigo in CODIGOS:
        nombre_corto = codigo.nombre.split(" (")[0]
        info = versiones.get(codigo.archivo, {})
        url = info.get("url") or codigo.url
        actual = LEGAL_CORPUS_DIR / codigo.archivo
        resultado = {"codigo": nombre_corto, "estado": "", "detalle": ""}

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / "nuevo.pdf"
            try:
                avisar(f"Revisando {nombre_corto}…")
                _bajar(url, tmp)
                if not _es_el_codigo(tmp, codigo) and codigo.buscar_en_edomex:
                    url = _buscar_en_edomex(codigo, tmp, avisar)
                    if url is None:
                        raise ValueError("no se encontró en el sitio oficial")
                if not _es_el_codigo(tmp, codigo):
                    raise ValueError("el PDF oficial no tiene el titulo esperado")

                reforma = ultima_reforma(tmp)
                # La primera vez que se revisa un codigo se indexa aunque el PDF
                # sea igual, para que sus fragmentos lleven la fecha de reforma.
                cambio = (
                    not actual.exists()
                    or _huella(tmp) != _huella(actual)
                    or "actualizado" not in info
                )
                info.update(url=url, revisado=ahora, ultima_reforma=reforma or info.get("ultima_reforma"))

                if cambio:
                    avisar(f"Actualizando {nombre_corto} (reforma {reforma or 'sin fecha'}); tarda unos minutos…")
                    LEGAL_CORPUS_DIR.mkdir(exist_ok=True)
                    respaldo = actual.with_suffix(".pdf.anterior")
                    if actual.exists():
                        actual.replace(respaldo)
                    tmp.replace(actual)
                    try:
                        n = indexar_codigo(codigo, reforma)
                    except Exception:
                        # Si falla el indexado, se regresa el PDF anterior.
                        if respaldo.exists():
                            respaldo.replace(actual)
                        raise
                    respaldo.unlink(missing_ok=True)
                    info["actualizado"] = ahora
                    resultado.update(estado="actualizado", detalle=f"Última reforma: {reforma or 'sin fecha'} ({n} fragmentos)")
                else:
                    resultado.update(estado="al_dia", detalle=f"Última reforma: {reforma or 'sin fecha'}")
            except Exception as e:
                info["error"] = str(e) if isinstance(e, SinRespuesta) else f"Error inesperado: {e}"
                resultado.update(estado="error", detalle=str(e))
            else:
                info.pop("error", None)

        versiones[codigo.archivo] = info
        _guardar_versiones(versiones)
        resultados.append(resultado)

    return resultados


# --- Programacion: revision automatica cada mes -----------------------------
#
# programacion.json guarda cuando fue la ultima revision (manual o
# automatica) y cuando toca la siguiente: la ultima + 1 mes. Si la ultima
# fallo (sin internet, sitio caido), se reintenta al dia siguiente.
#
# El programador corre dentro del servidor: mientras la app este abierta,
# cada hora checa si ya toca. Si la Mac estuvo apagada el dia que tocaba, se
# hace en cuanto se vuelva a abrir la app.

PROGRAMACION = LEGAL_CORPUS_DIR / "programacion.json"
REVISAR_CADA_SEG = int(os.getenv("LEYES_REVISAR_CADA_SEG", "3600"))
ESPERA_INICIAL_SEG = int(os.getenv("LEYES_ESPERA_INICIAL_SEG", "60"))


def sumar_un_mes(fecha: datetime) -> datetime:
    """20 oct -> 20 nov; 31 ene -> 28/29 feb (ultimo dia si el mes es mas corto)."""
    import calendar

    anio, mes = (fecha.year + 1, 1) if fecha.month == 12 else (fecha.year, fecha.month + 1)
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


def leer_programacion() -> dict:
    if PROGRAMACION.exists():
        return json.loads(PROGRAMACION.read_text(encoding="utf-8"))
    # Primera vez: si ya se habia revisado a mano, se toma esa fecha.
    revisados = [v["revisado"] for v in leer_versiones().values() if v.get("revisado")]
    if revisados:
        ultima = datetime.fromisoformat(max(revisados))
        return {
            "ultima_ejecucion": ultima.isoformat(timespec="seconds"),
            "origen": "manual",
            "resultado": None,
            "proxima_ejecucion": sumar_un_mes(ultima).isoformat(timespec="seconds"),
        }
    return {"ultima_ejecucion": None, "origen": None, "resultado": None,
            "proxima_ejecucion": datetime.now().isoformat(timespec="seconds")}


def _registrar_ejecucion(origen: str, resultado: str, hubo_errores: bool) -> None:
    ahora = datetime.now().replace(microsecond=0)
    proxima = ahora + timedelta(days=1) if hubo_errores else sumar_un_mes(ahora)
    LEGAL_CORPUS_DIR.mkdir(exist_ok=True)
    PROGRAMACION.write_text(json.dumps({
        "ultima_ejecucion": ahora.isoformat(),
        "origen": origen,
        "resultado": resultado,
        "proxima_ejecucion": proxima.isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def ya_toca() -> bool:
    proxima = leer_programacion().get("proxima_ejecucion")
    return proxima is None or datetime.now() >= datetime.fromisoformat(proxima)


_programador_iniciado = False


def iniciar_programador() -> None:
    """Hilo que, cada REVISAR_CADA_SEG, revisa si ya toca la actualizacion
    mensual y la lanza. Se llama una vez al arrancar el servidor."""
    global _programador_iniciado
    if _programador_iniciado:
        return
    _programador_iniciado = True

    def ciclo():
        import time

        time.sleep(ESPERA_INICIAL_SEG)  # que primero termine de arrancar la app
        while True:
            try:
                if ya_toca():
                    iniciar_actualizacion(origen="automatica")
            except Exception:
                pass  # nunca debe tumbar el servidor; se reintenta en la siguiente vuelta
            time.sleep(REVISAR_CADA_SEG)

    threading.Thread(target=ciclo, daemon=True, name="leyes-mensual").start()


# --- Trabajo en segundo plano (para el boton) --------------------------------

_lock = threading.Lock()
estado = {"corriendo": False, "origen": None, "mensaje": "", "inicio": None, "fin": None, "resultados": []}


def iniciar_actualizacion(origen: str = "manual") -> bool:
    """Arranca la revision en un hilo. Regresa False si ya habia una corriendo.
    `origen`: "manual" (boton) o "automatica" (programador mensual)."""
    with _lock:
        if estado["corriendo"]:
            return False
        estado.update(corriendo=True, origen=origen, resultados=[],
                      mensaje="Revisión mensual automática: empezando…" if origen == "automatica" else "Empezando…",
                      inicio=datetime.now().isoformat(timespec="seconds"), fin=None)

    def avisar(msg: str):
        estado["mensaje"] = msg

    def trabajo():
        try:
            estado["resultados"] = revisar_y_actualizar(avisar)
            actualizados = [r["codigo"] for r in estado["resultados"] if r["estado"] == "actualizado"]
            errores = [r["codigo"] for r in estado["resultados"] if r["estado"] == "error"]
            if errores:
                estado["mensaje"] = (
                    f"No se pudo revisar: {', '.join(errores)}. Se sigue usando la versión "
                    "anterior; intenta de nuevo más tarde."
                    + (f" Se actualizó: {', '.join(actualizados)}." if actualizados else "")
                )
            elif actualizados:
                estado["mensaje"] = f"Se actualizó: {', '.join(actualizados)}."
            else:
                estado["mensaje"] = "Todo está al día."
        except Exception as e:  # algo inesperado; que no se quede "corriendo"
            estado["mensaje"] = f"Error: {e}"
        finally:
            hubo_errores = not estado["resultados"] or any(
                r["estado"] == "error" for r in estado["resultados"]
            )
            try:
                _registrar_ejecucion(origen, estado["mensaje"], hubo_errores)
            except Exception:
                pass
            estado["corriendo"] = False
            estado["fin"] = datetime.now().isoformat(timespec="seconds")

    threading.Thread(target=trabajo, daemon=True).start()
    return True
