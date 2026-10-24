"""
Tipo de escrito (demanda, contestacion, alegatos, contrato...).

Se usa en dos lados con LAS MISMAS reglas:
  - al indexar, para etiquetar cada escrito del despacho
    (por su nombre de archivo y el inicio del texto), y
  - al chatear, para saber que tipo de escrito esta pidiendo la usuaria y
    buscar ejemplos solo de ese tipo.

Sin esto, la busqueda por parecido traia promociones del mismo juicio (todas
empiezan con el mismo rubro) en vez del tipo de escrito pedido.

El orden importa: gana la primera regla que coincide (por ejemplo,
"contestacion de demanda" debe ser contestacion, no demanda).
"""

import re
from typing import Optional

REGLAS: list[tuple[str, str]] = [
    ("contrato", r"\bcontrato|\bpermuta|promesa de venta|\bmandato\b"),
    ("convenio", r"\bconvenio"),
    ("contestacion", r"contestaci[oó]n|se contesta|reconvencional"),
    ("alegatos", r"\balegatos"),
    ("pruebas", r"\bpruebas\b|ofrecimiento|tacha de testigos"),
    ("interrogatorio", r"interrogatori|repreguntas|pliego de p|posiciones"),
    ("copias", r"\bcopias\b"),
    ("causa_ejecutoria", r"caus[oaeó]\s*ejecutori"),
    ("rebeldia", r"rebeld[ií]a"),
    ("autorizacion_abogados", r"autorizaci[oó]n|nombra.{0,10}abogad|patrocinio|personalidad del mandatario|amplia poder"),
    ("exhorto", r"exhorto"),
    ("desahogo_vista", r"\bvista\b|desahog"),
    ("amparo", r"\bamparo"),
    ("denuncia", r"denuncia|carpeta de investigaci|allanamiento|\brobo\b|querella"),
    ("demanda", r"\bdemanda|divorcio|rectificaci[oó]n de acta|nulidad|guarda y custodia|concubinato|pretensiones|medios preparatorios|plenario de pose|juicio (ejecutivo )?mercantil|mercantil\b"),
    ("oficio", r"\boficio|solicitud de archivo|\barchivo\b"),
]

_COMPILADAS = [(tipo, re.compile(pat, re.I)) for tipo, pat in REGLAS]


def detectar_tipo(texto: str) -> Optional[str]:
    """Regresa el primer tipo cuyas palabras aparecen en `texto`, o None."""
    for tipo, pat in _COMPILADAS:
        if pat.search(texto):
            return tipo
    return None


_PRESENTE = re.compile(r"P\s*R\s*E\s*S\s*E\s*N\s*T\s*E", re.I)
# En el cuerpo, "demanda" solo cuenta si de verdad se esta demandando: el
# rubro de CUALQUIER promocion del juicio dice "JUICIO: DIVORCIO..." y no
# por eso es la demanda.
_DEMANDA_EN_CUERPO = re.compile(
    r"vengo a (demandar|promover)|demando (de|a|en|al|la)|en la v[ií]a", re.I
)


def tipo_de_escrito(nombre_archivo: str, contenido: str) -> str:
    """Tipo de un escrito del despacho: primero por el nombre del archivo
    (la Lic. los nombra muy descriptivos); si no, por el cuerpo del escrito,
    brincandose el rubro (expediente, juicio, partes, juez)."""
    tipo = detectar_tipo(nombre_archivo)
    if tipo and tipo != "demanda":
        return tipo

    m = _PRESENTE.search(contenido[:1500])
    cuerpo = contenido[m.end():m.end() + 800] if m else contenido[:800]
    tipo_cuerpo = detectar_tipo(cuerpo)
    if tipo_cuerpo == "demanda" and not _DEMANDA_EN_CUERPO.search(cuerpo):
        tipo_cuerpo = None

    if tipo == "demanda":
        # El nombre dice "divorcio", "rectificacion"... pero si el cuerpo
        # muestra que es otra cosa (una vista, unas copias), gana el cuerpo.
        return tipo_cuerpo or "demanda"
    return tipo_cuerpo or "promocion"
