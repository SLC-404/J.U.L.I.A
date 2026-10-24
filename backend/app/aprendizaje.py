"""
El asistente aprende de los escritos FINALES de la Lic. Juana.

Cuando ella corrige un escrito a mano ("Editar") y lo exporta a Word, esa
version se copia a escritos_despacho/aprendidos/ y se agrega a la coleccion
"escritos" de Chroma (categoria "aprendido"). La proxima vez que se pida un
escrito del mismo tipo, se usa de modelo PRIMERO lo que ella ya aprobo, antes
que los escritos viejos de la USB.

Solo aprende de lo que ella reviso (editado a mano): los borradores sin
revisar del modelo no se usan como ejemplo, para no copiar sus errores.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from app.tipos_escrito import tipo_de_escrito

BASE_DIR = Path(__file__).resolve().parent.parent
ESCRITOS_DIR = BASE_DIR / "escritos_despacho"
APRENDIDOS_DIR = ESCRITOS_DIR / "aprendidos"
REGISTRO = APRENDIDOS_DIR / "registro.jsonl"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def fue_editado_a_mano(created_at: datetime, updated_at: datetime | None) -> bool:
    return bool(updated_at and created_at and (updated_at - created_at).total_seconds() > 2)


def aprender(docx: Path, texto: str, cliente: str, servicio: str, message_id: int) -> str:
    """Guarda el escrito final como modelo y lo indexa. Regresa la ruta
    relativa (dentro de escritos_despacho/) con que quedo."""
    import chromadb
    from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore

    APRENDIDOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = APRENDIDOS_DIR / f"msg{message_id}_{docx.name}"
    shutil.copy2(docx, destino)
    archivo = str(destino.relative_to(ESCRITOS_DIR))
    tipo = tipo_de_escrito(docx.name, texto)

    Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text", base_url=OLLAMA_HOST)
    Settings.node_parser = SentenceSplitter(chunk_size=1000, chunk_overlap=100)
    collection = chromadb.PersistentClient(path=str(BASE_DIR / "chroma_db")).get_or_create_collection("escritos")
    # Si ya se habia aprendido una version de este mismo mensaje, se reemplaza.
    collection.delete(where={"mensaje": message_id})

    doc = Document(
        text=f"{servicio}\n{texto}",
        metadata={"archivo": archivo, "cliente": cliente, "categoria": "aprendido",
                  "tipo": tipo, "mensaje": message_id},
    )
    doc.excluded_embed_metadata_keys = list(doc.metadata)
    doc.excluded_llm_metadata_keys = list(doc.metadata)
    VectorStoreIndex.from_documents(
        [doc], storage_context=StorageContext.from_defaults(vector_store=ChromaVectorStore(chroma_collection=collection))
    )

    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps({"archivo": archivo, "cliente": cliente, "servicio": servicio, "tipo": tipo,
                            "mensaje": message_id, "fecha": datetime.now().isoformat(timespec="seconds")},
                           ensure_ascii=False) + "\n")
    return archivo
