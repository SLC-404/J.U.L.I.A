"""
Indexa los escritos del despacho (los de la Lic. Juana) en Chroma, en la
coleccion "escritos", para que el asistente los use como MODELO de
estructura y estilo al redactar.

Lee backend/escritos_despacho/manifiesto.csv y solo indexa las filas con
usar_en_asistente = "si" (escritos de clientes, asuntos propios, mercantiles
y formatos; NO tareas de la escuela, documentos personales ni duplicados).
Para sacar o meter un archivo, cambia esa columna en el CSV (se puede abrir
en Excel/Numbers) y vuelve a correr este script.

Correr (necesita Ollama encendido):

    cd backend
    source .venv/bin/activate
    python scripts/ingest_escritos.py

Borra y vuelve a crear la coleccion cada vez, asi que no deja duplicados.
"""

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.text_extract import extract_text
from app.tipos_escrito import tipo_de_escrito

BASE_DIR = Path(__file__).resolve().parent.parent
ESCRITOS_DIR = BASE_DIR / "escritos_despacho"
MANIFIESTO = ESCRITOS_DIR / "manifiesto.csv"
CHROMA_DIR = BASE_DIR / "chroma_db"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
COLECCION = "escritos"


def main():
    if not MANIFIESTO.exists():
        print(f"No encontre {MANIFIESTO}. Primero hay que ordenar los escritos.")
        return

    Settings.embed_model = OllamaEmbedding(
        model_name="nomic-embed-text", base_url=OLLAMA_HOST
    )
    # Pedazos de ~1000 tokens: nomic-embed-text en Ollama corta lo que pase
    # de ~2000, y asi cada pedazo conserva varios parrafos seguidos.
    Settings.node_parser = SentenceSplitter(chunk_size=1000, chunk_overlap=100)

    with open(MANIFIESTO, encoding="utf-8-sig") as f:
        filas = [r for r in csv.DictReader(f) if r["usar_en_asistente"] == "si"]

    docs = []
    for r in filas:
        path = ESCRITOS_DIR / r["copiado_a"]
        try:
            text = extract_text(path).strip()
        except Exception as e:  # un archivo danado no debe tumbar la ingesta
            print(f"[saltado] {r['copiado_a']}: {e}")
            continue
        if len(text) < 200:
            continue
        doc = Document(
            text=text,
            metadata={
                "archivo": r["copiado_a"],
                "cliente": r["cliente"] or r["categoria"],
                "categoria": r["categoria"],
                "tipo": tipo_de_escrito(Path(r["copiado_a"]).name, text),
            },
        )
        # Que la busqueda se base solo en el contenido del escrito, no en el
        # nombre del cliente ni en la ruta del archivo.
        doc.excluded_embed_metadata_keys = ["archivo", "cliente", "categoria", "tipo"]
        doc.excluded_llm_metadata_keys = ["archivo", "cliente", "categoria", "tipo"]
        docs.append(doc)

    # Escritos finales que la Lic. reviso en la app (app/aprendizaje.py).
    registro = ESCRITOS_DIR / "aprendidos" / "registro.jsonl"
    if registro.exists():
        import json
        vistos = {}
        for linea in registro.read_text(encoding="utf-8").splitlines():
            r = json.loads(linea)
            vistos[r["mensaje"]] = r  # el ultimo de cada mensaje
        for r in vistos.values():
            path = ESCRITOS_DIR / r["archivo"]
            if not path.exists():
                continue
            doc = Document(text=f"{r['servicio']}\n{extract_text(path)}",
                           metadata={"archivo": r["archivo"], "cliente": r["cliente"],
                                     "categoria": "aprendido", "tipo": r["tipo"], "mensaje": r["mensaje"]})
            doc.excluded_embed_metadata_keys = list(doc.metadata)
            doc.excluded_llm_metadata_keys = list(doc.metadata)
            docs.append(doc)

    from collections import Counter
    print("Tipos:", dict(Counter(d.metadata["tipo"] for d in docs).most_common()))
    print(f"Indexando {len(docs)} escritos (tarda unos minutos)...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLECCION)
    except Exception:
        pass  # no existia todavia
    collection = client.get_or_create_collection(COLECCION)
    storage = StorageContext.from_defaults(
        vector_store=ChromaVectorStore(chroma_collection=collection)
    )
    VectorStoreIndex.from_documents(docs, storage_context=storage, show_progress=True)
    print(f"Listo: {collection.count()} fragmentos en la coleccion '{COLECCION}'.")


if __name__ == "__main__":
    main()
