"""
Revision automatica de lo que escribe el modelo, ANTES de mostrarlo.

El modelo a veces deforma el nombre del cliente (en el caso de María
Pérez escribio "MARIA PERES" en las 5 versiones). Aqui se busca en el
texto cualquier nombre muy parecido al del cliente (mismos apellidos, nombre
casi igual) y se cambia por el correcto.
"""

import difflib
import re
import unicodedata
from datetime import date, timedelta

_U = "A-ZÁÉÍÓÚÑÜa-záéíóúñü"


def _clave(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def corregir_nombre(texto: str, nombre: str) -> str:
    """Cambia variantes mal escritas del nombre del cliente por el correcto
    (respetando si venia en MAYUSCULAS o en Titulo)."""
    partes = nombre.split()
    if len(partes) < 3:
        return texto  # sin dos apellidos no es seguro adivinar
    nombres, apellidos = partes[:-2], partes[-2:]
    # <tantas palabras como nombres de pila> + los dos apellidos exactos
    patron = re.compile(
        rf"\b((?:[{_U}]+\s+){{{len(nombres)}}}){re.escape(apellidos[0])}\s+{re.escape(apellidos[1])}\b",
        re.I,
    )
    nombres_k = _clave(" ".join(nombres))

    def reemplazar(m: re.Match) -> str:
        visto = m.group(0)
        visto_nombres_k = _clave(m.group(1))
        if visto_nombres_k == nombres_k:
            return visto  # ya esta bien escrito
        if difflib.SequenceMatcher(None, visto_nombres_k, nombres_k).ratio() >= 0.75:
            return nombre.upper() if visto.isupper() else nombre
        return visto  # otra persona con los mismos apellidos (ej. un hermano)

    return patron.sub(reemplazar, texto)


DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def contexto_de_fechas(hoy: date | None = None) -> str:
    """Para que "fecha del lunes" salga bien: el modelo no sabe que dia es."""
    hoy = hoy or date.today()
    proximos = []
    for i in range(1, 8):
        d = hoy + timedelta(days=i)
        if d.weekday() < 5:  # lunes a viernes
            proximos.append(f"el próximo {DIAS[d.weekday()]} es {d.day} de {MESES[d.month - 1]} de {d.year}")
    return (
        f"Hoy es {fecha_larga(hoy)}. "
        + "; ".join(proximos)
        + '. Si piden "la fecha del lunes" (u otro día), usa esa fecha escrita así: '
        '"a 26 de octubre de 2026".'
    )


# --- Saltos de linea --------------------------------------------------------
# En el modo corregir, el modelo a veces regresa el escrito en un solo bloque
# ("... comparezco para exponer: H E C H O S 1.- Que ... 2.- Que ..."). El
# Word sale ilegible. Se vuelven a poner los saltos antes de cada parte.

_ANTES = [
    r"JUICIO\s*:", r"ACTOR\s*:", r"V\.\s*S\.,?", r"DEMANDAD[OA]\s*:",
    r"C\.\s*JUEZ\b", r"P\s*R\s*E\s*S\s*E\s*N\s*T\s*E\s*:",
    r"H\s*E\s*C\s*H\s*O\s*S\b", r"D\s*E\s*R\s*E\s*C\s*H\s*O\b(?!\s+(?:a|de|que)\b)",
    r"Fundan la presente", r"Norman el procedimiento",
    r"(?:Por lo (?:anteriormente )?expuesto|En m[ée]rito de lo expuesto)",
    r"(?:PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[ÉE]PTIMO|OCTAVO)\s*\.\s*-",
    r"PROTESTO\s+LO\s+NECESARIO", r"ABOGAD[OA]\s+PATRON[OA]",
]
_SALTO = re.compile(r"(?<=\S)[ \t,]+(?=(?:" + "|".join(_ANTES) + r"))")
_HECHO = re.compile(r"(?<=[.;:])[ \t]+(?=\d{1,2}\s*\.\s*-\s)")  # " 2.- Que..."
_TRAS_PRESENTE = re.compile(r"(P\s*R\s*E\s*S\s*E\s*N\s*T\s*E\s*:)[ \t]+(?=\S)")
_TRAS_TITULO = re.compile(r"\b(H\s*E\s*C\s*H\s*O\s*S|D\s*E\s*R\s*E\s*C\s*H\s*O)[ \t]+(?=(?:\d|Fundan|Que|El|La|Con)\b)")
_TRAS_PROTESTO = re.compile(r"(PROTESTO\s+LO\s+NECESARIO\.?)[ \t]+(?=\S)")
# "... a 26 de octubre de 2026 MARÍA PÉREZ LÓPEZ" -> nombre en su renglon
_FECHA_Y_NOMBRE = re.compile(r"(de \d{4}\.?)[ \t]+(?=[A-ZÁÉÍÓÚÑ]{3,}\s+[A-ZÁÉÍÓÚÑ]{3,})")


def reacomodar_renglones(texto: str) -> str:
    """Solo actua si el escrito viene "aplastado" (pocos renglones para su
    tamano); si ya trae sus saltos, no se toca."""
    renglones = [r for r in texto.splitlines() if r.strip()]
    if len(renglones) >= max(8, len(texto) // 900):
        return texto
    t = _SALTO.sub("\n", texto)
    t = _HECHO.sub("\n", t)
    t = _TRAS_PRESENTE.sub(r"\1\n", t)
    t = _TRAS_TITULO.sub(r"\1\n", t)
    t = _TRAS_PROTESTO.sub(r"\1\n", t)
    t = _FECHA_Y_NOMBRE.sub(r"\1\n", t)
    return re.sub(r"\n{3,}", "\n\n", t)


# --- Rubro --------------------------------------------------------------------
# El modelo a veces escribe el rubro en un solo renglon ("EXPEDIENTE No. 123/2026,
# JUICIO: ..., ACTOR:, V.S., DEMANDADO: ...") o pone actor/demandado en un
# sucesorio, donde no hay contraparte.

_CAMPO_RUBRO = re.compile(r"(EXPEDIENTE\s*(?:No\.?|N[ÚU]MERO)?\s*:?|JUICIO\s*:?|ACTOR(?:A)?\s*:|V\.\s*S\.|DEMANDAD[OA]\s*:)", re.I)
_FIN_RUBRO = re.compile(r"C\.\s*JUEZ|^\s*JUEZ\b|P\s*R\s*E\s*S\s*E\s*N\s*T\s*E|C\.\s*AGENTE|A\s+QUIEN", re.I | re.M)


def arreglar_rubro(texto: str, es_sucesorio: bool, cliente: str = "") -> str:
    fin = _FIN_RUBRO.search(texto[:1500])
    if not fin or not _CAMPO_RUBRO.search(texto[: fin.start()]):
        return texto
    rubro, resto = texto[: fin.start()], texto[fin.start():]
    piezas = _CAMPO_RUBRO.split(rubro)
    lineas = []
    for etiqueta, valor in zip(piezas[1::2], piezas[2::2]):
        valor = valor.strip(" ,;:\n\t")
        etiqueta = " ".join(etiqueta.split())
        es_parte = re.match(r"(ACTOR|V\.\s*S|DEMANDAD)", etiqueta, re.I)
        if es_sucesorio and es_parte:
            continue  # en un sucesorio no hay actor ni demandado
        if es_parte and not re.match(r"V\.\s*S", etiqueta, re.I) and not valor:
            continue  # "ACTOR:" vacio
        if re.match(r"JUICIO", etiqueta, re.I) and not etiqueta.endswith(":"):
            etiqueta = "JUICIO:"
        if es_sucesorio and cliente and re.match(r"JUICIO", etiqueta, re.I):
            # "...A BIENES DE JUAN PÉREZ GÓMEZ: MARÍA PÉREZ LÓPEZ"
            valor = re.sub(rf"[\s,:;-]+{re.escape(cliente)}\s*$", "", valor, flags=re.I)
        lineas.append(f"{etiqueta} {valor}".strip(" :") if not valor else f"{etiqueta} {valor}".strip())
    # "V.S." solo tiene sentido entre ACTOR y DEMANDADO
    if not any(l.upper().startswith("ACTOR") for l in lineas) or not any(l.upper().startswith("DEMANDAD") for l in lineas):
        lineas = [l for l in lineas if not re.match(r"V\.\s*S", l, re.I)]
    return "\n".join(lineas) + "\n" + resto.lstrip()


# --- Fecha ----------------------------------------------------------------------
# "a lunes 23 de octubre de 2026": el 23 es viernes. Si el dia de la semana no
# cuadra con el numero, gana el dia de la semana (la abogada pidio "el lunes")
# y se pone la fecha del proximo dia con ese nombre.

_DIA_FECHA = re.compile(
    r"\b(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)\s+(\d{1,2})\s+de\s+("
    + "|".join(MESES) + r")\s+de\s+(\d{4})",
    re.I,
)


def corregir_fecha(texto: str, hoy: date | None = None) -> str:
    hoy = hoy or date.today()
    nombres = [_clave(d) for d in DIAS]

    def arreglar(m: re.Match) -> str:
        dia_sem = nombres.index(_clave(m.group(1)))
        try:
            fecha = date(int(m.group(4)), MESES.index(m.group(3).lower()) + 1, int(m.group(2)))
        except ValueError:
            fecha = None
        if fecha and fecha.weekday() == dia_sem:
            return m.group(0)
        d = hoy + timedelta(days=1)
        while d.weekday() != dia_sem:
            d += timedelta(days=1)
        return f"{m.group(1)} {d.day} de {MESES[d.month - 1]} de {d.year}"

    return _DIA_FECHA.sub(arreglar, texto)


# --- Genero de quien promueve -----------------------------------------------------
# Si la clienta es mujer, "el suscrito / soy hijo / fui notificado" -> femenino.
# Solo se tocan frases en primera persona de quien promueve.

def es_mujer(nombre: str) -> bool:
    primero = _clave(nombre).split()[0] if nombre.strip() else ""
    return primero.endswith("a") and primero not in {"luca", "nikita", "bautista"}


_A_FEMENINO = [
    (r"\bel suscrito\b", "la suscrita"), (r"\bEl suscrito\b", "La suscrita"),
    (r"\bEL SUSCRITO\b", "LA SUSCRITA"), (r"\bal suscrito\b", "a la suscrita"),
    (r"\bdel suscrito\b", "de la suscrita"),
    (r"\b(la suscrita|soy)\s+hijo\b", r"\1 hija"),
    (r"\b(la suscrita)\s+es\s+hijo\b", r"\1 es hija"),
    (r"\bfui notificado\b", "fui notificada"),
    (r"\b(la suscrita)\s+fue\s+notificado\b", r"\1 fue notificada"),
    (r"\b(la suscrita)\s+como\s+hijo(\s+leg[ií]timo)?\b", lambda m: m.group(1) + " como hija" + (" legítima" if m.group(2) else "")),
    (r"\bse notific[oó] al suscrito\b", "se notificó a la suscrita"),
    (r"\b(la suscrita)\s+fue\s+apersonado\b", r"\1 fue apersonada"),
    (r"\b(la suscrita)\s+como\s+heredero\s+leg[ií]timo\b", r"\1 como heredera legítima"),
    (r"\bpor apersonado\b", "por apersonada"),
    (r"\bSe me tenga por APERSONADO\b", "Se me tenga por APERSONADA"),
]


def ajustar_genero(texto: str, nombre_cliente: str) -> str:
    if not es_mujer(nombre_cliente):
        return texto
    for patron, cambio in _A_FEMENINO:
        texto = re.sub(patron, cambio, texto)
    return texto


# --- Otros arreglos fijos -------------------------------------------------------------
def quitar_bajo_la_clave(texto: str) -> str:
    """Regla del despacho: no "bajo la clave de EXPEDIENTE No. 123/2026"."""
    texto = re.sub(r"bajo la clave(?: de)?\s+(?:EXPEDIENTE\s+)?(?:No\.?|n[uú]mero)?\s*", "en el expediente número ", texto, flags=re.I)
    return re.sub(r"(?:con|bajo)\s+(?:el\s+)?n[uú]mero\s+(\d{1,5}/\d{2,4})", r"en el expediente número \1", texto, flags=re.I)


_PROTESTO_JUNTO = re.compile(r"(PROTESTO\s+LO\s+NECESARIO\.?)[ \t]+(?=\S)")
_ABOGADO_JUNTO = re.compile(r"(?<=\S)[ \t]+(?=ABOGAD[OA]\s+PATRON)")


def separar_firma(texto: str) -> str:
    """Siempre: 'P R E S E N T E:' y la firma ('PROTESTO LO NECESARIO',
    lugar/fecha, cliente y abogada) en renglones propios, aunque el resto del
    escrito venga bien."""
    texto = re.sub(r"(?<=\S)[ \t]+(P\s*R\s*E\s*S\s*E\s*N\s*T\s*E\s*:)", r"\n\1", texto)
    texto = _PROTESTO_JUNTO.sub(r"\1\n", texto)
    texto = _ABOGADO_JUNTO.sub("\n", texto)
    return _FECHA_Y_NOMBRE.sub(r"\1\n", texto)


# --- Lineas de derecho --------------------------------------------------------------
_FUNDAN = re.compile(r"^\s*(Fundan la presente|Norman el procedimiento)\b.*$", re.I | re.M)
_TITULO_DERECHO = re.compile(r"^\s*D\s*E\s*R\s*E\s*C\s*H\s*O\s*:?\s*$", re.I | re.M)


def poner_lineas_de_derecho(texto: str, lineas: list[str]) -> str:
    """Cambia los renglones 'Fundan la presente...'/'Norman el procedimiento...'
    del modelo por los que arma la app (articulos correctos y del codigo
    correcto). Si el modelo no los escribio, los pone bajo 'D E R E C H O'."""
    if not lineas:
        return texto
    if _FUNDAN.search(texto):
        primero = _FUNDAN.search(texto)
        texto = _FUNDAN.sub("", texto)
        texto = texto[: primero.start()] + "\n".join(lineas) + texto[primero.start():]
        return re.sub(r"\n{3,}", "\n\n", texto)
    titulo = _TITULO_DERECHO.search(texto)
    if titulo:
        return texto[: titulo.end()] + "\n" + "\n".join(lineas) + texto[titulo.end():]
    return texto


# --- Datos que la abogada da en el chat --------------------------------------------
# El juzgado y el domicilio a veces solo estan en el chat ("EL JUZGADO ES: JUEZ
# SEGUNDO CIVIL...", "AÑADE EL DOMICILIO: VICTORIANO GONZALEZ # 201..."). El
# modelo no siempre los copia; la app los saca y los pone ella misma.

_JUZGADO_CHAT = re.compile(
    r"(JUEZ\s+[A-ZÁÉÍÓÚÑ0-9 ,.]{5,200}?RESIDENCIA\s+EN\s+[A-ZÁÉÍÓÚÑ ]{3,40}?)(?=\s*(?:[.;\n]|$|,\s*[A-ZÁÉÍÓÚÑ]{2,}\s*:))",
    re.I,
)
_DOMICILIO_CHAT = re.compile(r"DOMICILIO[^:\n]{0,60}:\s*([^\n]{8,150}?)(?:\.\s|\n|$)", re.I)


_PALABRAS_JUZGADO = [
    "JUEZ", "JUZGADO", "PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "CIVIL", "FAMILIAR",
    "MERCANTIL", "PRIMERA", "INSTANCIA", "DISTRITO", "JUDICIAL", "RESIDENCIA", "TENANGO", "VALLE",
    "SANTIAGO", "TIANGUISTENCO", "TOLUCA", "ESTADO", "MEXICO", "MÉXICO", "CUANTIA", "MENOR",
]


def _corregir_palabras(texto: str) -> str:
    """'ISNTANCIA' -> 'INSTANCIA' (errores de dedo en el juzgado que se escribio en el chat)."""
    def arreglar(m: re.Match) -> str:
        w = m.group(0)
        if len(w) < 6 or w in _PALABRAS_JUZGADO:
            return w
        parecida = difflib.get_close_matches(w, _PALABRAS_JUZGADO, n=1, cutoff=0.8)
        return parecida[0] if parecida else w
    return re.sub(r"[A-ZÁÉÍÓÚÑ]+", arreglar, texto)


def datos_del_chat(mensajes_usuario: list[str]) -> dict:
    """Juzgado y domicilio mas recientes que la abogada escribio en el chat."""
    datos: dict = {}
    for m in mensajes_usuario:
        j = _JUZGADO_CHAT.search(m)
        if j:
            datos["juzgado"] = _corregir_palabras(" ".join(j.group(1).split()).strip(" ,.").upper())
        d = _DOMICILIO_CHAT.search(m)
        if d:
            datos["domicilio"] = " ".join(d.group(1).split()).strip(" ,.;")
    return datos


_BLOQUE_JUEZ = re.compile(
    r"^[ \t]*(?:C\.\s*)?(?:JUEZ|C\.\s*JUEZ)[^\n]*(?:\n(?!\s*P\s*R\s*E\s*S\s*E\s*N\s*T\s*E)[^\n]*){0,3}?(?=\n\s*P\s*R\s*E\s*S\s*E\s*N\s*T\s*E)",
    re.I | re.M,
)
_PROEMIO_DOMICILIO = re.compile(
    r"(se[ñn]alando como domicilio para o[ií]r y recibir (?:toda clase de )?notificaciones(?: legales)?)\s+([^;]{3,200}?)(;)",
    re.I,
)


def poner_juzgado(texto: str, juzgado: str | None) -> str:
    if not juzgado:
        return texto
    return _BLOQUE_JUEZ.sub(lambda m: f"C. {juzgado}.", texto, count=1)


def poner_domicilio(texto: str, domicilio: str | None) -> str:
    if not domicilio:
        return texto

    def cambiar(m: re.Match) -> str:
        if _clave(domicilio)[:15] in _clave(m.group(2)):
            return m.group(0)  # ya lo trae
        return f"{m.group(1)} el ubicado en {domicilio}{m.group(3)}"

    return _PROEMIO_DOMICILIO.sub(cambiar, texto, count=1)


# --- Articulos que la abogada pidio quitar ----------------------------------------
_PIDE_QUITAR = re.compile(r"quita|quitalo|quítalo|no va|tampoco|elimina|borra|sin el", re.I)
_NUM_ARTICULO = re.compile(r"\b(\d{1,2}\.\d{1,4})\b")


def articulos_excluidos(mensajes_usuario: list[str]) -> set[str]:
    """'EL FUNDAMENTO LEGAL 4.25 QUITALO, NO VA Y ESTE TAMPOCO 6.144' -> {4.25, 6.144}.
    Solo cuenta numeros en renglones donde pide quitar algo."""
    fuera: set[str] = set()
    for m in mensajes_usuario:
        for renglon in re.split(r"\n+", m):
            if _PIDE_QUITAR.search(renglon):
                fuera.update(_NUM_ARTICULO.findall(renglon))
    return fuera


def quitar_articulos(texto: str, excluidos: set[str]) -> str:
    """Borra de la explicacion del DERECHO las frases que citan articulos que
    la abogada pidio quitar (el modelo los volvia a meter)."""
    for n in excluidos:
        num = re.escape(n)
        # frase entre separadores (; o .) que menciona "articulo 4.25"
        texto = re.sub(
            rf"(?:(?<=[.;])|^)[^.;\n]*\bart[ií]culos?\s+{num}\b[^.;\n]*[.;]?",
            "", texto, flags=re.I | re.M,
        )
        # numero suelto en listas: "4.24, 4.25 y 4.26"
        texto = re.sub(rf",\s*{num}\b|\b{num}\s*,\s*|\s+y\s+{num}\b", "", texto)
    texto = re.sub(r";\s*;", ";", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    # "...legitima. y el articulo 4.43..." -> "...legitima. El articulo 4.43..."
    texto = re.sub(r"(\.\s+)y\s+(\w)", lambda m: m.group(1) + m.group(2).upper(), texto)
    return texto


# --- Hechos: renumerar y cambiar de orden (sin el modelo) -------------------------
# "EL 1 CAMBIA POR EL 3": el modelo borraba un hecho y dejaba "1.-, 3.-". Estas
# operaciones las hace la app al instante.

_TITULO_HECHOS = re.compile(r"^\s*H\s*E\s*C\s*H\s*O\s*S\s*:?\s*$", re.I | re.M)
_FIN_HECHOS = re.compile(
    r"^\s*(D\s*E\s*R\s*E\s*C\s*H\s*O|P\s*R\s*U\s*E\s*B\s*A\s*S|P\s*R\s*E\s*S\s*T\s*A\s*C|Por lo (anteriormente )?expuesto|En m[ée]rito)",
    re.I | re.M,
)
_INICIO_HECHO = re.compile(r"^(\s*)(\d{1,2})\s*\.\s*-\s*", re.M)


def _partir_hechos(texto: str):
    """(antes, [hechos], despues) o None si no hay seccion de hechos numerados."""
    t = _TITULO_HECHOS.search(texto)
    if not t:
        return None
    fin = _FIN_HECHOS.search(texto, t.end())
    cuerpo = texto[t.end(): fin.start() if fin else len(texto)]
    marcas = list(_INICIO_HECHO.finditer(cuerpo))
    if not marcas:
        return None
    antes = texto[: t.end()] + cuerpo[: marcas[0].start()]
    hechos = []
    for i, m in enumerate(marcas):
        fin_h = marcas[i + 1].start() if i + 1 < len(marcas) else len(cuerpo)
        hechos.append(cuerpo[m.end(): fin_h].strip())
    despues = "\n\n" + texto[fin.start():] if fin else ""
    return antes, hechos, despues


def _unir_hechos(antes: str, hechos: list[str], despues: str) -> str:
    cuerpo = "\n".join(f"{i}.- {h}" for i, h in enumerate(hechos, 1))
    return antes.rstrip("\n") + "\n" + cuerpo + despues


def renumerar_hechos(texto: str) -> str:
    partes = _partir_hechos(texto)
    if not partes:
        return texto
    return _unir_hechos(*partes)


_CAMBIO_ORDEN = re.compile(
    r"\b(?:hecho\s*|el\s*)?(\d{1,2})\s*(?:cambia|intercambia|cambialo|cámbialo|lo cambias|va|pasa|pásalo|pasalo|mueve|muevelo|muévelo)\s*"
    r"(?:de lugar\s*)?(?:por|con|a|al|en|en lugar del?|a la posici[oó]n)\s*(?:el\s*)?(?:hecho\s*)?(?:lugar\s*)?(?:del?\s*)?(\d{1,2})\b",
    re.I,
)


def aplicar_cambio_de_orden(texto: str, pedido: str) -> str | None:
    """'EL 1 CAMBIA POR EL 3' -> intercambia los hechos 1 y 3 del escrito.
    Regresa el escrito cambiado, o None si el pedido no es de este tipo."""
    m = _CAMBIO_ORDEN.search(pedido)
    if not m or not re.search(r"hecho|orden", pedido, re.I) and len(pedido) > 60:
        return None
    partes = _partir_hechos(texto)
    if not partes:
        return None
    antes, hechos, despues = partes
    a, b = int(m.group(1)) - 1, int(m.group(2)) - 1
    if not (0 <= a < len(hechos) and 0 <= b < len(hechos)) or a == b:
        return None
    hechos[a], hechos[b] = hechos[b], hechos[a]
    return _unir_hechos(antes, hechos, despues)


def quitar_expediente_inventado(texto: str, validos: set[str]) -> str:
    """'EXPEDIENTE No. 123/2026' en una demanda nueva: el numero lo inventa el
    modelo. Si no viene en las notas ni en el chat, se deja en blanco."""
    def cambiar(m: re.Match) -> str:
        return m.group(0) if m.group(2) in validos else m.group(1).rstrip()
    texto = re.sub(r"(EXPEDIENTE\s*No\.?)\s*\[No\.?\]", r"\1", texto, flags=re.I)  # resto del modelo anonimizado
    return re.sub(r"(EXPEDIENTE\s*(?:No\.?|N[ÚU]MERO)?\s*:?\s*)(\d{1,5}/\d{2,4})", cambiar, texto, count=1, flags=re.I)
