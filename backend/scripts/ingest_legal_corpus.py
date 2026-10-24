"""
Indexa (o vuelve a indexar) en Chroma los codigos legales que ya estan en
backend/legal_corpus/. La lista de codigos y sus fuentes oficiales vive en
app/leyes.py.

Normalmente NO hace falta correr esto: el boton "Buscar actualizaciones" de
la pantalla Leyes baja los PDFs oficiales y reindexa solo lo que cambio.
Sirve para reconstruir todo desde cero (por ejemplo, si se borro chroma_db/).

    cd backend
    source .venv/bin/activate
    python scripts/ingest_legal_corpus.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import leyes


def main():
    versiones = leyes.leer_versiones()
    for codigo in leyes.CODIGOS:
        path = leyes.LEGAL_CORPUS_DIR / codigo.archivo
        if not path.exists():
            print(f"[saltado] falta {codigo.archivo}: usa el boton 'Buscar actualizaciones'")
            continue
        reforma = leyes.ultima_reforma(path)
        print(f"Indexando {codigo.nombre.split(' (')[0]} (reforma {reforma or 'sin fecha'})...")
        n = leyes.indexar_codigo(codigo, reforma)
        info = versiones.setdefault(codigo.archivo, {})
        info.update(ultima_reforma=reforma, actualizado=datetime.now().isoformat(timespec="seconds"))
        print(f"  -> {n} fragmentos")
    leyes._guardar_versiones(versiones)
    print("Listo.")


if __name__ == "__main__":
    main()
