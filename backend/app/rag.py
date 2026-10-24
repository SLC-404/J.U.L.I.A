"""
Capa de RAG: busca en Chroma lo que le sirve al asistente antes de
preguntarle a Ollama. Hay dos colecciones:

- "leyes": fragmentos de los codigos (scripts/ingest_legal_corpus.py).
- "escritos": los escritos reales del despacho de la Lic. Juana
  (scripts/ingest_escritos.py), para que el asistente copie su estructura y
  su estilo.

Si alguna coleccion todavia no existe, su funcion regresa None y el chat
sigue funcionando sin ese contexto.
"""

import os
import re
from pathlib import Path
from typing import Optional

from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

import chromadb

from app.text_extract import extract_text
from app.tipos_escrito import detectar_tipo

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"
ESCRITOS_DIR = BASE_DIR / "escritos_despacho"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# Tope de caracteres por escrito de ejemplo (~2,000 tokens): suficiente para
# ver la estructura completa de casi cualquier promocion sin llenar la
# memoria del modelo.
MAX_CHARS_EJEMPLO = 7000

_indexes: dict[str, Optional[VectorStoreIndex]] = {}


def _get_index(name: str) -> Optional[VectorStoreIndex]:
    """Carga la coleccion `name` de Chroma una sola vez (lazy) y la reutiliza."""
    if name in _indexes:
        return _indexes[name]
    _indexes[name] = None

    if not CHROMA_DIR.exists():
        return None

    Settings.embed_model = OllamaEmbedding(
        model_name="nomic-embed-text", base_url=OLLAMA_HOST
    )
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = chroma_client.get_or_create_collection(name)
    if collection.count() == 0:
        return None

    _indexes[name] = VectorStoreIndex.from_vector_store(
        ChromaVectorStore(chroma_collection=collection)
    )
    return _indexes[name]


def get_legal_context(query: str, top_k: int = 4) -> Optional[str]:
    """
    Busca los fragmentos de ley mas parecidos a `query`. Regresa un texto
    listo para pegar en el prompt (con el nombre del codigo de donde sale
    cada fragmento), o None si todavia no hay nada indexado.
    """
    index = _get_index("leyes")
    if index is None:
        return None

    nodes = index.as_retriever(similarity_top_k=top_k).retrieve(query)
    if not nodes:
        return None

    partes = []
    for n in nodes:
        codigo = n.node.metadata.get("codigo", "ley no identificada")
        reforma = n.node.metadata.get("ultima_reforma")
        if reforma and reforma != "sin fecha":
            codigo += f", texto vigente con ultima reforma del {reforma}"
        partes.append(f"[{codigo}]\n{n.node.get_content().strip()}")

    return "\n\n---\n\n".join(partes)


_U = "A-ZÁÉÍÓÚÑÜ"
# Una palabra de nombre en mayusculas (o inicial "M."), que no sea parte
# del rubro (V.S., DEMANDADO, JUICIO...).
_PALABRA = rf"(?!V\.?\s*S\b|DEMANDAD|ACTOR|JUICIO|EXPEDIENTE|JUEZ\b|C\.)(?:[{_U}]{{2,}}|[{_U}]\.)"
_NOMBRE = rf"{_PALABRA}(?:\s+(?:Y/O\s+|DE\s+(?:LA\s+|LOS\s+)?)?{_PALABRA}){{1,5}}"
_CAMPOS_RUBRO = re.compile(
    rf"(?:ACTOR(?:A)?|DEMANDAD[OA]|OFENDID[OA]|SENTENCIADO|IMPUTADO|V\.\s*S\.?)\s*:?\s*(?:C\.\s*|SRA?\.\s*)?({_NOMBRE})"
)
_PROMOVENTE = re.compile(
    rf"P\s*R\s*E\s*S\s*E\s*N\s*T\s*E\s*[:.;]?\s*(?:C\.\s*|SRA?\.\s*)?({_NOMBRE})\s*,"
)
_EXPEDIENTE = re.compile(r"(EXPEDIENTE\s*(?:No\.?|N[ÚU]MERO)?\s*:?\s*)[\w/.-]*\d[\w/.-]*", re.I)
# Nombres que SI deben quedarse: la abogada del despacho y su equipo.
_DEL_DESPACHO = ("JUANA LANDA", "JESUS GERARDO ARMAS", "ELIZABETH DE LA TORRE", "MICHAEL SEGURA")


def _anonimizar(text: str) -> str:
    """Quita de un escrito de ejemplo los nombres de las partes y el numero
    de expediente, para que el modelo no los copie en el escrito nuevo."""
    nombres = set()
    for m in _CAMPOS_RUBRO.finditer(text[:2500]):
        nombres.add(m.group(1).strip(" ."))
    m = _PROMOVENTE.search(text[:3000])
    if m:
        nombres.add(m.group(1).strip(" ."))
    for nombre in sorted(nombres, key=len, reverse=True):
        if len(nombre.split()) < 2 or any(d in nombre.upper() for d in _DEL_DESPACHO):
            continue
        partes = [re.escape(p) for p in nombre.split()]
        text = re.sub(r"\s+".join(partes), "[NOMBRE]", text, flags=re.I)
    return _EXPEDIENTE.sub(r"\1[No.]", text)


def get_style_examples(query: str, pedido: str = "", max_docs: int = 1) -> list[str]:
    """
    Busca los escritos del despacho mas parecidos a `query` y regresa el
    texto COMPLETO (recortado y sin nombres de las partes) de hasta
    `max_docs` escritos distintos, para usarlos como modelo. Se manda el
    escrito entero y no solo el pedazo que coincidio porque lo valioso es la
    estructura: rubro, proemio, hechos, derecho, puntos petitorios y firma.

    `pedido` es lo que escribio la usuaria: si ahi se nota el tipo de
    escrito ("la demanda", "alegatos", "copias certificadas"...), se buscan
    ejemplos SOLO de ese tipo.
    """
    index = _get_index("escritos")
    if index is None:
        return []

    nodes = []
    tipo = detectar_tipo(pedido)
    if tipo:
        # Primero los que la Lic. ya reviso y aprobo (app/aprendizaje.py)...
        aprobados = MetadataFilters(filters=[ExactMatchFilter(key="tipo", value=tipo),
                                             ExactMatchFilter(key="categoria", value="aprendido")])
        nodes = [n for n in index.as_retriever(similarity_top_k=3, filters=aprobados).retrieve(query)
                 if (n.score or 0) >= 0.6]
        # ...si no hay, los de la USB del mismo tipo.
        if not nodes:
            filtro = MetadataFilters(filters=[ExactMatchFilter(key="tipo", value=tipo)])
            nodes = index.as_retriever(similarity_top_k=8, filters=filtro).retrieve(query)
    if not nodes:
        nodes = index.as_retriever(similarity_top_k=8).retrieve(query)

    archivos: list[str] = []
    for n in nodes:
        archivo = n.node.metadata.get("archivo")
        if archivo and archivo not in archivos:
            archivos.append(archivo)
        if len(archivos) == max_docs:
            break

    ejemplos = []
    for archivo in archivos:
        try:
            text = extract_text(ESCRITOS_DIR / archivo).strip()
        except Exception:
            continue  # se borro o se movio el archivo; no es grave
        text = re.sub(r"\n\s*\n+", "\n", _anonimizar(text))
        if len(text) > MAX_CHARS_EJEMPLO:
            text = text[:MAX_CHARS_EJEMPLO] + "\n[... el escrito sigue ...]"
        ejemplos.append(text)
    return ejemplos
