"""
Saca el texto de un escrito (.docx, .doc o .pdf). Lo usan la ingesta de
escritos del despacho y el RAG para mostrar un escrito completo de ejemplo.
"""

import subprocess
import sys
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".docx":
        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    if ext == ".doc":
        return _doc_viejo(path)
    if ext == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return ""


def _doc_viejo(path: Path) -> str:
    """.doc viejo de Word. macOS trae `textutil`, que lo convierte sin
    instalar nada; en Windows se le pide al Word de la Lic. (pywin32). Si no
    se puede, regresa "" (ese escrito no sirve de ejemplo, pero no truena)."""
    if sys.platform == "win32":
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()  # cada hilo de FastAPI necesita su propio COM
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            try:
                doc = word.Documents.Open(str(path.resolve()), ReadOnly=True, AddToRecentFiles=False)
                texto = doc.Content.Text
                doc.Close(False)
            finally:
                word.Quit()
            return texto.replace("\r", "\n")
        except Exception as e:
            print(f"[texto] no se pudo leer {path.name} con Word: {e}")
            return ""
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    return result.stdout
