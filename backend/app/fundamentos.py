"""
Fundamento legal para cada escrito.

Antes la busqueda de leyes usaba solo el ultimo mensaje y traia articulos
generales (1.1-1.8 del Codigo de Procedimientos) aunque el caso fuera un
sucesorio. Ahora, para cada servicio, se sabe de que CAPITULOS de cada codigo
sale su fundamento (mapa TEMAS, hecho con el indice real de los codigos):

  - Codigo Civil (sustantivo): "Fundan la presente los articulos..."
  - Codigo de Procedimientos Civiles (procesal): "Norman el procedimiento..."

Dentro de esos capitulos se eligen los articulos mas parecidos a lo que se
pide (servicio + notas del caso + mensaje), y se agregan algunos "ancla" que
siempre deben estar (ej. 4.44 en un sucesorio: plazo de 30 dias para que los
presuntos herederos justifiquen sus derechos).
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from app.articulos import clave, leer_biblioteca
from app.leyes import BIBLIOTECA_DIR, CODIGOS, leer_versiones

CC = "codigo_civil_edomex.pdf"
CPC = "codigo_procedimientos_civiles_edomex.pdf"
CNP = "codigo_nacional_procedimientos_civiles_familiares.pdf"

# servicio -> {codigo: [partes del Libro/Titulo/Capitulo que aplican]}
TEMAS: dict[str, dict[str, list[str]]] = {
    "divorcio incausado": {
        CC: ["titulo tercero del divorcio", "capitulo iii de los alimentos"],
        CPC: ["capitulo ix del divorcio incausado"],
    },
    "divorcio voluntario": {
        CC: ["titulo tercero del divorcio"],
        CPC: ["del divorcio por mutuo consentimiento"],
    },
    "guarda y custodia y pension alimenticia": {
        CC: ["de los alimentos", "titulo septimo de la patria potestad"],
        CPC: ["libro quinto de las controversias sobre el estado civil"],
    },
    "pension alimenticia": {
        CC: ["de los alimentos", "registro de deudores alimentarios"],
        CPC: ["libro quinto de las controversias sobre el estado civil"],
    },
    "perdida de la patria potestad": {
        CC: ["titulo septimo de la patria potestad"],
        CPC: ["conclusion de patria potestad", "libro quinto de las controversias sobre el estado civil"],
    },
    "controversia del orden familiar": {
        CC: ["libro cuarto del derecho familiar"],
        CPC: ["libro quinto de las controversias sobre el estado civil"],
    },
    "liquidacion de sociedad conyugal": {
        CC: ["de la sociedad conyugal", "titulo tercero del divorcio"],
        CPC: ["de los incidentes", "libro quinto de las controversias sobre el estado civil"],
    },
    "juicio sucesorio intestamentario": {
        CC: [
            "libro sexto de las sucesiones / titulo primero",
            "de la sucesion legitima",
            "de la aceptacion y de la repudiacion",
            # (albaceas: es una etapa posterior; traia el 6.243, que no aplica)
        ],
        CPC: ["de los intestados"],  # (cap. I traia el 4.25 -acumulacion-, que no aplica)
    },
    "informacion ad perpetuam (concubinato)": {
        CC: ["del concubinato", "de la sucesion de los concubinos"],
        CPC: ["procedimientos judiciales no contenciosos"],
    },
    "rectificacion de acta": {
        CC: ["de la rectificacion de las", "del nombre de las personas", "libro tercero del registro civil / titulo primero"],
        CPC: ["libro quinto de las controversias sobre el estado civil"],
    },
    "nulidad y cancelacion de acta": {
        CC: ["libro tercero del registro civil"],
        CPC: ["libro quinto de las controversias sobre el estado civil"],
    },
    "plenario de posesion": {
        CC: ["titulo tercero de la posesion"],
        CPC: ["capitulo i de las acciones", "del juicio ordinario", "de la contestacion de la demanda"],
    },
    "juicio ordinario civil": {
        CPC: ["capitulo i de las acciones", "del juicio ordinario", "de la notificacion de la demanda"],
    },
    "medios preparatorios a juicio": {
        CPC: ["de los medios preparatorios a juicio"],
    },
    "contrato de compraventa": {CC: ["de la compraventa", "de los contratos en general / capitulo i"]},
    "contrato de promesa de venta": {CC: ["de la promesa", "de la compraventa / capitulo i"]},
    "contrato de donacion": {CC: ["de las donaciones"]},
    "contrato de arrendamiento": {CC: ["del arrendamiento"]},
    "contrato de permuta": {CC: ["de la permuta"]},
    "contrato de mandato": {CC: ["del mandato"]},
    "convenio": {CC: ["de las transacciones", "de los contratos en general"]},
    "copias certificadas y tramites de expediente": {
        CPC: ["de las formalidades judiciales", "de la presentacion de escritos"],
    },
}

# Articulos que SIEMPRE deben ir para ese servicio (verificados en el texto).
ANCLAS: dict[str, dict[str, list[str]]] = {
    "juicio sucesorio intestamentario": {
        CC: ["6.1", "6.2", "6.142"],  # la Lic. quito el 6.144
        CPC: ["4.42", "4.43", "4.44", "4.45"],
    },
    "divorcio incausado": {CPC: ["2.373", "2.374"]},
    "divorcio voluntario": {CPC: ["2.275"]},
}

# Materias que NO estan en los codigos cargados: se avisa al modelo para que
# no cite articulos de memoria.
FALTAN: dict[str, str] = {
    "juicio ejecutivo mercantil": "el Código de Comercio",
    "juicio ordinario mercantil": "el Código de Comercio",
    "denuncia penal": "el Código Penal del Estado de México y el Código Nacional de Procedimientos Penales",
    "defensa penal": "el Código Nacional de Procedimientos Penales",
    "juicio de amparo": "la Ley de Amparo",
}

POR_CODIGO = int(os.getenv("FUNDAMENTO_POR_CODIGO", "7"))
MAX_CHARS_ARTICULO = 1100


def _texto(nodo_texto: str) -> str:
    if len(nodo_texto) > MAX_CHARS_ARTICULO:
        return nodo_texto[:MAX_CHARS_ARTICULO].rsplit(" ", 1)[0] + " […]"
    return nodo_texto


def _numeros_del_tema(archivo: str, partes: list[str]) -> list[str]:
    partes_k = [clave(p) for p in partes]
    return [
        a.articulo
        for a in leer_biblioteca(archivo, BIBLIOTECA_DIR)
        if not a.derogado and any(p in clave(a.ubicacion) for p in partes_k)
    ]


@dataclass
class Fundamento:
    texto: str  # lo que se le pasa al modelo (articulos completos)
    # Los que la app pone en "Fundan la presente.../Norman el procedimiento...":
    # las anclas + los 2 mas parecidos de los capitulos del tema (sin los
    # "extra" de todo el codigo, que a veces son ruido).
    citas: dict[str, list[str]] = field(default_factory=dict)


def _orden(numero: str):
    partes = numero.split(" ")[0].split(".")
    return [int(p) if p.isdigit() else 0 for p in partes]


def lineas_de_derecho(citas: dict[str, list[str]]) -> list[str]:
    """'Fundan la presente los articulos ... del Codigo Civil...' y 'Norman el
    procedimiento los articulos ... del Codigo de Procedimientos...'."""
    def lista(nums: list[str]) -> str:
        nums = sorted(dict.fromkeys(nums), key=_orden)
        return nums[0] if len(nums) == 1 else ", ".join(nums[:-1]) + " y " + nums[-1]

    cc, cpc = citas.get(CC), citas.get(CPC)
    lineas = []
    if cc:
        lineas.append(
            f"Fundan la presente los artículos {lista(cc)} y demás relativos y aplicables "
            "del Código Civil del Estado de México."
        )
    if cpc:
        verbo = "Norman el procedimiento" if cc else "Fundan la presente"
        lineas.append(
            f"{verbo} los artículos {lista(cpc)} y demás relativos y aplicables del "
            "Código de Procedimientos Civiles del Estado de México."
        )
    return lineas


# Segun el TIPO de escrito (no el servicio): requisitos procesales que deben
# cumplirse siempre.
ANCLAS_POR_TIPO: dict[str, dict[str, list[str]]] = {
    "demanda": {CPC: ["2.108", "2.104"]},  # requisitos de la demanda; documentos
    "contestacion": {CPC: ["2.115", "2.116"]},
}
FAMILIARES = {
    "divorcio incausado", "divorcio voluntario", "guarda y custodia y pension alimenticia",
    "pension alimenticia", "perdida de la patria potestad", "controversia del orden familiar",
    "liquidacion de sociedad conyugal",
}


def fundamento(
    servicio: Optional[str], notas: Optional[str], pedido: str, excluir: Optional[set[str]] = None,
    tipo_escrito: Optional[str] = None,
) -> Optional[Fundamento]:
    """Articulos que el modelo puede citar, agrupados por codigo (sustantivo
    y procesal), y los que la app cita en el DERECHO. None si las leyes no
    estan indexadas."""
    from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters

    from app.rag import _get_index

    index = _get_index("leyes")
    if index is None:
        return None

    excluir = excluir or set()  # articulos que la abogada pidio quitar en el chat
    s_key = clave(servicio or "")
    tema = TEMAS.get(s_key, {})
    anclas = {a: list(nums) for a, nums in ANCLAS.get(s_key, {}).items()}
    for a, nums in ANCLAS_POR_TIPO.get(tipo_escrito or "", {}).items():
        anclas.setdefault(a, [])
        anclas[a] += [n for n in nums if n not in anclas[a]]
        if tipo_escrito == "demanda" and s_key in FAMILIARES and a == CPC:
            anclas[a].append("5.40")  # demandas familiares: Libro Quinto
    anclas = {a: [n for n in nums if n not in excluir] for a, nums in anclas.items()}
    consulta = f"{servicio or ''}. {notas or ''} {pedido}"[:1500]
    versiones = leer_versiones()

    def buscar(archivo: str, numeros: Optional[list[str]], k: int):
        filtros = [MetadataFilter(key="archivo", value=archivo)]
        if numeros is not None:
            filtros.append(MetadataFilter(key="articulo", value=numeros, operator=FilterOperator.IN))
        return index.as_retriever(
            similarity_top_k=k, filters=MetadataFilters(filters=filtros)
        ).retrieve(consulta)

    secciones = []
    citas: dict[str, list[str]] = {}
    for c in CODIGOS:
        if c.archivo == CNP and s_key not in (
            "divorcio incausado", "guarda y custodia y pension alimenticia",
            "pension alimenticia", "perdida de la patria potestad", "controversia del orden familiar",
        ):
            continue  # el Nacional solo como referencia en lo familiar (transicion)

        # Si el servicio esta en el mapa y este codigo no le toca (ej. un
        # contrato no necesita el Codigo de Procedimientos), se salta.
        if tema and not tema.get(c.archivo) and not anclas.get(c.archivo) and c.archivo != CNP:
            continue

        elegidos: dict[str, str] = {}
        a_citar: list[str] = []
        # 1) anclas
        if anclas.get(c.archivo):
            for n in buscar(c.archivo, anclas[c.archivo], len(anclas[c.archivo])):
                elegidos[n.node.metadata["articulo"]] = n.node.get_content()
                a_citar.append(n.node.metadata["articulo"])
        # 2) lo mas parecido dentro de los capitulos del tema
        if tema.get(c.archivo):
            numeros = _numeros_del_tema(c.archivo, tema[c.archivo])
            if numeros:
                for i, n in enumerate(buscar(c.archivo, numeros[:400], POR_CODIGO)):
                    num = n.node.metadata["articulo"]
                    elegidos.setdefault(num, n.node.get_content())
                    # Si el servicio ya tiene articulos clave para este codigo, se
                    # citan SOLO esos (la Lic. marco el 4.25 -acumulacion- como
                    # ajeno a un apersonamiento); si no, los 2 mas parecidos.
                    if i < 2 and num not in a_citar and not anclas.get(c.archivo):
                        a_citar.append(num)
        if a_citar and c.archivo != CNP:
            citas[c.archivo] = a_citar
        # 3) un par de lo mas parecido en todo el codigo (por si el tema no lo cubre)
        extra = 2 if (tema.get(c.archivo) or anclas.get(c.archivo)) else (3 if c.archivo != CNP else 2)
        if c.archivo == CNP:
            extra = 2
        for n in buscar(c.archivo, None, extra):
            elegidos.setdefault(n.node.metadata["articulo"], n.node.get_content())

        for n in excluir:
            elegidos.pop(n, None)
        if c.archivo in citas:
            citas[c.archivo] = [n for n in citas[c.archivo] if n not in excluir] or citas.pop(c.archivo) and []
        if not elegidos:
            continue
        reforma = versiones.get(c.archivo, {}).get("ultima_reforma")
        nombre = c.nombre.split(" (")[0]
        papel = {
            CC: "derecho sustantivo: 'Fundan la presente los artículos…'",
            CPC: "procedimiento: 'Norman el procedimiento los artículos…'",
            CNP: "solo referencia; confirmar si ya aplica en el Edomex",
        }[c.archivo]

        cuerpo = "\n\n".join(_texto(elegidos[n]) for n in sorted(elegidos, key=_orden))
        secciones.append(
            f"=== {nombre}" + (f" (última reforma: {reforma})" if reforma else "") + f" — {papel} ===\n{cuerpo}"
        )

    aviso = ""
    if s_key in FALTAN:
        aviso = (
            f"\n\nOJO: este asunto se rige por {FALTAN[s_key]}, que NO está cargado. No cites "
            "artículos de esa ley de memoria: escribe [fundamento: artículos de "
            f"{FALTAN[s_key]}] para que la abogada los complete."
        )
    if not secciones:
        return Fundamento(aviso.strip(), {}) if aviso else None
    return Fundamento("\n\n".join(secciones) + aviso, citas)
