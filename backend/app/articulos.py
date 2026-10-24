"""
Separa un codigo (PDF) en ARTICULOS, cada uno con su numero, su epigrafe
(el titulito que la ley pone arriba, ej. "Citacion a los presuntos
herederos") y donde vive (Libro / Titulo / Capitulo).

Antes los codigos se indexaban en pedazos de ~2,500 caracteres que mezclaban
muchos articulos; la busqueda traia reglas generales (arts. 1.1-1.8) en vez
de los del tema. Por articulo, el asistente recibe el texto exacto con su
numero, y se puede pedir "los del capitulo De los Intestados".

La "biblioteca" de articulos se guarda en legal_corpus/articulos/<codigo>.json
para buscar por capitulo sin pasar por la base vectorial.
"""

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader

# Renglones que se repiten en cada pagina y no son parte de la ley.
_RUIDO = re.compile(
    r"^\s*("
    r"Publicad[ao] en el Peri[oó]dico Oficial.*|"
    r"[ÚU]ltima reforma.*|"
    r"Sentencia SCJN.*|"
    r"C[ÓO]DIGO (CIVIL|DE PROCEDIMIENTOS CIVILES) DEL ESTADO DE M[ÉE]XICO\s*|"
    r"C[ÓO]DIGO NACIONAL DE PROCEDIMIENTOS CIVILES Y FAMILIARES\s*|"
    r"C[ÁA]MARA DE DIPUTADOS DEL H\. CONGRESO DE LA UNI[ÓO]N\s*|"
    r"Secretar[ií]a General\s*|"
    r"Secretar[ií]a de Servicios Parlamentarios\s*|"
    r"\d{1,4}\s*(de\s+\d{1,4})?\s*"  # numero de pagina
    r")$",
    re.I,
)
# "Artículo 4.44.- texto"  (a veces el PDF parte el numero: "6.1 61.-" = 6.161)
_ARTICULO = re.compile(
    r"^\s*Art[ií]culo\s+(\d+(?:\s*\.\s*\d+(?:\s\d{1,3})?)?)\s*(Bis|Ter|Qu[aá]ter)?\s*\.?\s*-\s*(.*)$", re.I
)
# "Artículo 167. texto" (Codigo Nacional) o "Artículo 4.5. Derogado."
_ARTICULO_PUNTO = re.compile(
    r"^\s*Art[ií]culo\s+(\d+(?:\.\d+)?)\s*(Bis|Ter|Qu[aá]ter)?\s*\.\s*(.*)$", re.I
)
_DEROGADO = re.compile(r"^\s*(se\s+)?derogad?[oa]?\.?\s*$", re.I)


def _es_articulo(linea: str):
    return _ARTICULO.match(linea) or _ARTICULO_PUNTO.match(linea)


# "TITULO SEGUNDO", "CAPITULO III", "Libro Cuarto"... solo si sigue un
# ordinal o numero romano (si no, "titulo de propiedad..." parecia encabezado).
_ENCABEZADO = re.compile(
    r"^\s*(LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N)\s+"
    r"([IVXLl]+\b|[ÚU]NIC|PRIMER|SEGUND|TERCER|CUART|QUINT|SEXT|S[ÉE]PTIM|OCTAV|NOVEN|D[ÉE]CIM|UND[ÉE]CIM|DUOD[ÉE]CIM)",
    re.I,
)
_TRANSITORIOS = re.compile(
    r"^\s*(ART[ÍI]CULOS\s+)?T\s*R\s*A\s*N\s*S\s*I\s*T\s*O\s*R\s*I\s*O\s*S\s*$", re.I
)


@dataclass
class Articulo:
    articulo: str  # "4.44" o "167"
    epigrafe: str
    libro: str
    titulo: str
    capitulo: str
    texto: str

    @property
    def derogado(self) -> bool:
        return len(self.texto) < 40 and bool(_DEROGADO.match(self.texto or "derogado"))

    @property
    def ubicacion(self) -> str:
        return " / ".join(x for x in (self.libro, self.titulo, self.capitulo) if x)


def clave(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def _lineas(pdf: Path) -> list[str]:
    reader = PdfReader(str(pdf))
    out = []
    for page in reader.pages:
        for linea in (page.extract_text() or "").splitlines():
            if linea.strip() and not _RUIDO.match(linea):
                out.append(linea.rstrip())
    return out


def separar_articulos(pdf: Path) -> list[Articulo]:
    lineas = _lineas(pdf)
    articulos: list[Articulo] = []
    libro = titulo = capitulo = ""
    actual: Articulo | None = None
    cuerpo: list[str] = []
    pendiente_encabezado: str | None = None  # "TITULO SEGUNDO" -> su nombre va en la linea siguiente
    previa = ""

    def cerrar():
        nonlocal actual, cuerpo
        if actual is not None:
            # El ultimo renglon corto del cuerpo suele ser el epigrafe del
            # SIGUIENTE articulo; ese se lo queda el siguiente.
            actual.texto = " ".join(" ".join(cuerpo).split())
            articulos.append(actual)
        actual, cuerpo = None, []

    for linea in lineas:
        if _TRANSITORIOS.match(linea):
            break  # los transitorios repiten numeros y no son el texto vigente

        m_enc = _ENCABEZADO.match(linea)
        # Un encabezado no trae punto y seguido ("Libro Segundo de este ordenamiento. Las..." es texto).
        if m_enc and len(linea) < 90 and not re.search(r"\.\s+\w", linea) and not linea.rstrip().endswith("."):
            nivel = clave(m_enc.group(1))
            resto = linea.strip()
            if nivel == "libro":
                libro, titulo, capitulo = resto, "", ""
            elif nivel == "titulo":
                titulo, capitulo = resto, ""
            elif nivel == "capitulo":
                capitulo = resto
            pendiente_encabezado = nivel
            previa = ""
            continue
        if pendiente_encabezado and not _es_articulo(linea) and len(linea) < 120:
            # nombre del libro/titulo/capitulo ("De los Intestados")
            if pendiente_encabezado == "libro":
                libro += " " + linea.strip()
            elif pendiente_encabezado == "titulo":
                titulo += " " + linea.strip()
            elif pendiente_encabezado == "capitulo":
                capitulo += " " + linea.strip()
            pendiente_encabezado = None
            continue
        pendiente_encabezado = None

        m = _es_articulo(linea)
        if m:
            epigrafe = ""
            if cuerpo and len(cuerpo[-1]) < 90 and not cuerpo[-1].rstrip().endswith((".", ";", ":")):
                epigrafe = cuerpo.pop().strip()
            elif actual is None and previa and len(previa) < 90:
                epigrafe = previa.strip()
            cerrar()
            numero = re.sub(r"\s+", "", m.group(1)) + (f" {m.group(2).capitalize()}" if m.group(2) else "")
            actual = Articulo(numero, epigrafe, " ".join(libro.split()), " ".join(titulo.split()),
                              " ".join(capitulo.split()), "")
            if m.group(3):
                cuerpo.append(m.group(3))
        elif actual is not None:
            cuerpo.append(linea.strip())
        previa = linea
    cerrar()
    return articulos


def guardar_biblioteca(archivo_pdf: str, articulos: list[Articulo], carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / (Path(archivo_pdf).stem + ".json")
    destino.write_text(json.dumps([asdict(a) for a in articulos], ensure_ascii=False), encoding="utf-8")
    return destino


def leer_biblioteca(archivo_pdf: str, carpeta: Path) -> list[Articulo]:
    ruta = carpeta / (Path(archivo_pdf).stem + ".json")
    if not ruta.exists():
        return []
    return [Articulo(**a) for a in json.loads(ruta.read_text(encoding="utf-8"))]
