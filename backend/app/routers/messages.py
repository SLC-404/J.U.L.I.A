"""
Chat del agente, SIEMPRE amarrado a un work (caso) especifico.

Cada mensaje de la abogada se atiende en uno de dos modos:

- ESCRITO NUEVO (no hay escrito en el caso, o pide "redacta/hazme otro..."):
  reglas del despacho + fundamento legal del servicio (app/fundamentos.py)
  + un escrito real del despacho del mismo tipo como modelo + datos del caso.

- CORRECCION (ya hay un escrito y pide cambios: "quita", "agrega",
  "coloca"...): se manda EL ULTIMO ESCRITO con la instruccion "aplica solo
  estos cambios". Antes cada correccion se volvia a escribir desde cero (con
  otro escrito modelo) y se perdian los cambios anteriores: en el caso de
  María el domicilio que dio la abogada desaparecio dos versiones
  despues.

Al final, app/revision.py corrige el nombre del cliente si el modelo lo
escribio mal.
"""

import re
import unicodedata
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.fundamentos import fundamento, lineas_de_derecho
from app.models import Client, Service, Work, WorkMessage
from app.ollama_client import chat
from app.rag import get_style_examples
from app.tipos_escrito import detectar_tipo
from app.revision import (
    ajustar_genero,
    aplicar_cambio_de_orden,
    articulos_excluidos,
    datos_del_chat,
    poner_domicilio,
    poner_juzgado,
    quitar_articulos,
    arreglar_rubro,
    contexto_de_fechas,
    corregir_fecha,
    corregir_nombre,
    poner_lineas_de_derecho,
    quitar_bajo_la_clave,
    quitar_expediente_inventado,
    reacomodar_renglones,
    renumerar_hechos,
    separar_firma,
)
from app.routers.ajustes import leer_reglas

router = APIRouter(prefix="/works/{work_id}/messages", tags=["chat"])

SYSTEM_PROMPT = (
    "Eres J.U.L.I.A. (Jurisprudencia Unificada, Leyes e Inteligencia Aplicada), "
    "el auxiliar legal del despacho de la LIC. JUANA LANDA HERNANDEZ "
    "(cedula profesional 3610993), abogada en Almoloya del Rio, Estado de "
    "Mexico. Redactas escritos legales (demandas, promociones, contratos, "
    "oficios) en espanol, con terminologia juridica mexicana precisa. Tus "
    "borradores los revisa la abogada: no agregues advertencias ni explicaciones, "
    "y nunca firmes ni menciones tu nombre dentro de un escrito.\n"
    "\n"
    "DATOS: no inventes. Nombres completos (tambien de hijos), fechas, numeros "
    "de acta o expediente, domicilios y montos van entre [corchetes] si no "
    "vienen en los datos del caso ni en lo que la abogada dijo en el chat. En "
    "los HECHOS escribe SOLO lo que dicen las notas del caso y el chat; no "
    "agregues sucesos, motivos ni conductas. Los HECHOS van en ORDEN "
    "CRONOLOGICO (lo mas antiguo primero), uno por numero. Escribe el nombre del "
    "cliente EXACTAMENTE como viene en los datos del caso.\n"
    "\n"
    "FUNDAMENTO LEGAL: te doy una lista de articulos (FUNDAMENTO LEGAL "
    "DISPONIBLE). Cita SOLO articulos de esa lista, con su numero exacto, y "
    "nunca de memoria. El apartado de derecho se escribe como lo hace el "
    "despacho:\n"
    "  D E R E C H O\n"
    "  Fundan la presente los articulos [numeros] y demas relativos y "
    "aplicables del Codigo Civil del Estado de Mexico.\n"
    "  Norman el procedimiento los articulos [numeros] y demas relativos y "
    "aplicables del Codigo de Procedimientos Civiles del Estado de Mexico.\n"
    "  Despues, en uno a tres parrafos, explica como aplican los articulos "
    "clave al caso (que dice el articulo y por que le da derecho al cliente), "
    "citando su contenido.\n"
    "Usa articulos de los DOS codigos (sustantivo y procesal) cuando sea un "
    "juicio. El proemio tambien puede decir 'ejercitando los derechos "
    "consignados en los articulos...'.\n"
    "\n"
    "FORMATO del despacho (texto normal, SIN Markdown ni asteriscos):\n"
    "- Rubro arriba: EXPEDIENTE No., JUICIO:, ACTOR:, V.S., DEMANDADO: (en "
    "sucesorios: JUICIO: SUCESORIO INTESTAMENTARIO A BIENES DE [causante], sin "
    "ACTOR ni DEMANDADO, porque no hay contraparte).\n"
    "- C. JUEZ ... (juzgado y residencia) y luego P R E S E N T E:\n"
    "- Proemio en PRIMERA PERSONA del cliente: 'NOMBRE, promoviendo por mi "
    "propio derecho y senalando como domicilio para oir y recibir toda clase "
    "de notificaciones ...; y autorizando ... ante usted de la manera mas "
    "atenta y respetuosa comparezco para exponer:'\n"
    "- 'H E C H O S' con hechos numerados '1.-', '2.-'; luego 'D E R E C H O'.\n"
    "- 'Por lo anteriormente expuesto y fundado, a usted C. Juez, atentamente "
    "pido:' y petitorios 'PRIMERO.-', 'SEGUNDO.-'...\n"
    "- 'PROTESTO LO NECESARIO' (escrito asi, sin letras separadas), lugar y "
    "fecha, nombre del cliente, y 'ABOGADO PATRONO / LIC. JUANA LANDA "
    "HERNANDEZ / CEDULA PROFESIONAL NO. 3610993'."
)

PROMPT_DEMANDA = (
    "ESTO ES UNA DEMANDA. Debe cumplir los requisitos del articulo 2.108 del "
    "Codigo de Procedimientos Civiles (te lo doy en el FUNDAMENTO) y llevar, en "
    "este orden:\n"
    "1. Rubro: EXPEDIENTE No. (en blanco), JUICIO: [tipo de juicio], ACTOR: "
    "[cliente], V.S., DEMANDADO: [contraparte].\n"
    "2. C. JUEZ ... y P R E S E N T E:\n"
    "3. Proemio: nombre del actor, 'promoviendo por mi propio derecho', "
    "domicilio para oir y recibir notificaciones, abogados autorizados, y 'vengo "
    "a demandar de [DEMANDADO], quien tiene su domicilio en [domicilio del "
    "demandado], en la via [tipo de juicio], las siguientes:'\n"
    "4. P R E S T A C I O N E S: A), B), C)... (lo que se reclama, concreto).\n"
    "5. H E C H O S: numerados, en orden cronologico, cada uno con fecha y lugar "
    "si se conocen; indica que documento prueba cada hecho ('lo que acredito con "
    "... que exhibo como anexo UNO').\n"
    "6. D E R E C H O: fondo (Codigo Civil) y procedimiento (Codigo de "
    "Procedimientos), y la competencia del juez.\n"
    "7. P R U E B A S: las que se ofrecen (documentales que se anexan, "
    "testimonial, confesional, etc.) relacionadas con los hechos.\n"
    "8. Puntos petitorios: PRIMERO.- tenerme por presentado demandando...; "
    "SEGUNDO.- emplazar al demandado...; TERCERO.- en su momento, dictar sentencia "
    "condenando a las prestaciones reclamadas.\n"
    "9. PROTESTO LO NECESARIO, lugar y fecha, firma.\n"
    "Lo que no venga en los datos del caso va entre [corchetes]."
)

PROMPT_CONSULTA = (
    "Eres J.U.L.I.A., la asesora legal del despacho de la LIC. JUANA LANDA HERNANDEZ "
    "(derecho civil y familiar, Estado de Mexico). La abogada te hace una "
    "PREGUNTA: contestala de forma clara y practica, en parrafos cortos o una "
    "lista, en espanol. NO redactes un escrito salvo que te lo pida.\n"
    "- Funda tu respuesta en los articulos de FUNDAMENTO LEGAL DISPONIBLE: di el "
    "numero y el codigo, y que dicen. Nunca inventes articulos.\n"
    "- Si la respuesta depende de un dato que no tienes (fechas, si hay "
    "testamento, etc.), dilo y explica que cambia en cada caso.\n"
    "- Si te pregunta que falta para un escrito, haz una lista concreta de datos "
    "y documentos.\n"
    "- Plazos: cita el articulo y explica desde cuando corre; aclara que la "
    "abogada debe confirmar el computo (dias habiles o naturales).\n"
    "- Termina con una linea 'Siguiente paso:' con lo que recomiendas hacer."
)

PROMPT_CORRECCION = (
    "Ahora vas a CORREGIR un escrito que ya existe. Reglas:\n"
    "- Aplica TODAS las indicaciones de la abogada y SOLO esas.\n"
    "- Todo lo demas se queda EXACTAMENTE igual que en el escrito actual "
    "(no reescribas, no quites ni agregues apartados por tu cuenta).\n"
    "- Si te pide agregar o mejorar el fundamento, usa SOLO articulos de la "
    "lista FUNDAMENTO LEGAL DISPONIBLE.\n"
    "- Responde SOLO con el escrito completo ya corregido."
)

# Palabras que indican que la abogada quiere cambiar el escrito actual.
_CORRECCION = re.compile(
    r"\b(quita|quitale|quitame|elimina|borra|omit[ea]|omitir|agrega|agregale|añade|anade|"
    r"coloca|pon|ponle|cambia|cambiale|corrige|sustituye|reemplaza|en lugar de|en vez de|"
    r"en esta parte|en el punto|aparte coloca|mejora|ajusta|modifica|justifica)\b",
    re.I,
)
# Palabras que indican que quiere un escrito distinto.
_NUEVO = re.compile(
    r"\b(redacta|redactame|redáctame|hazme|elabora|genera|prepara|nuevo escrito|otro escrito)\b",
    re.I,
)


class MessageIn(BaseModel):
    content: str


def _load_work_or_404(session: Session, work_id: int) -> Work:
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return work


def _clave(texto: str) -> str:
    """Para comparar nombres sin acentos ni mayusculas."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def _papel_del_cliente(nombre: str, notas: str) -> Optional[str]:
    """Si las notas dicen 'Actor: X vs. Demandado: Y', regresa si nuestro
    cliente es la parte actora o la demandada."""
    n, t = _clave(nombre), _clave(notas)
    actor = re.search(r"actor:\s*(.+?)\s+vs\.", t)
    dem = re.search(r"demandado:\s*(.+?)(?:\.\s|\.$|$)", t)
    if dem and n and n in dem.group(1):
        return "DEMANDADA"
    if actor and n and n in actor.group(1):
        return "ACTORA"
    return None


def _datos_del_caso(session: Session, work: Work, chat_datos: Optional[dict] = None) -> str:
    client = session.get(Client, work.client_id)
    service = session.get(Service, work.service_id)
    nombre = client.name if client else "[nombre del cliente]"
    texto = (
        f"DATOS DEL CASO. NUESTRO CLIENTE es {nombre.upper()} (escribe su nombre "
        "exactamente asi): el escrito lo promueve y lo firma el cliente, con la "
        "Lic. Juana como abogada patrono; nunca la contraparte. "
    )
    papel = _papel_del_cliente(nombre, work.notes or "")
    if papel:
        texto += f"En este juicio el cliente es la parte {papel}. "
    chat_datos = chat_datos or {}
    domicilio = (client.address if client else None) or chat_datos.get("domicilio")
    if chat_datos.get("juzgado"):
        texto += f"Juzgado (lo dio la abogada; cópialo exacto): C. {chat_datos['juzgado']}. "
    texto += (
        "Domicilio del cliente: "
        + (domicilio or "no registrado (si la abogada lo dio en el chat o ya está en el escrito, usa ese; si no, [domicilio])")
        + f". Servicio: {service.name if service else '[servicio]'}. "
        f"Notas del caso: {work.notes or 'sin notas'}."
    )
    return texto


_PREGUNTA = re.compile(
    r"\?|^\s*(qu[eé]|cu[aá]l|cu[aá]les|cu[aá]ndo|c[oó]mo|cu[aá]nto|d[oó]nde|por\s*qu[eé]|puedo|"
    r"podemos|se puede|es posible|hay que|tengo que|debo|explica|expl[ií]came|dime|me dices|"
    r"ay[uú]dame a entender|pregunta)\b",
    re.I,
)


def _es_consulta(mensaje: str) -> bool:
    """Pregunta de la abogada (no pide redactar ni corregir un escrito)."""
    if _NUEVO.search(mensaje) or _CORRECCION.search(mensaje):
        return False
    return bool(_PREGUNTA.search(mensaje))


def _es_correccion(mensaje: str, hay_escrito: bool) -> bool:
    if not hay_escrito:
        return False
    if _CORRECCION.search(mensaje):
        return True
    # "Redacta otro escrito..." sin palabras de correccion = escrito nuevo.
    return not _NUEVO.search(mensaje)


def _armar_mensajes(session: Session, work: Work, pedido: str) -> tuple[list[dict], str, dict]:
    """Regresa (mensajes para el modelo, modo, extras para la revision) donde
    modo es 'nuevo' o 'correccion'."""
    service = session.get(Service, work.service_id)
    servicio = service.name if service else None

    historial = session.exec(
        select(WorkMessage).where(WorkMessage.work_id == work.id).order_by(WorkMessage.created_at)
    ).all()
    ultimo_escrito = next(
        (m.content for m in reversed(historial) if m.role == "assistant" and m.tipo == "escrito"), None
    )
    if _es_consulta(pedido):
        modo = "consulta"
    elif _es_correccion(pedido, ultimo_escrito is not None):
        modo = "correccion"
    else:
        modo = "nuevo"
    # "Redacta la demanda... con su propuesta de convenio" sigue siendo demanda.
    es_demanda = modo == "nuevo" and bool(re.search(r"\bdemanda\b", pedido, re.I)) and not re.search(
        r"contestaci|contesta la|reconvenci", pedido, re.I
    )

    # Lo que la abogada dijo en el chat manda sobre lo automatico: articulos
    # que pidio quitar, juzgado y domicilio que dio.
    del_usuario = [m.content for m in historial if m.role == "user"] + [pedido]
    excluidos = articulos_excluidos(del_usuario)
    chat_datos = datos_del_chat(del_usuario)

    sistema = [PROMPT_CONSULTA if modo == "consulta" else SYSTEM_PROMPT]
    reglas = leer_reglas(session).strip()
    if reglas:
        sistema.append("REGLAS DEL DESPACHO (síguelas SIEMPRE):\n" + reglas)
    sistema.append(contexto_de_fechas())
    if modo == "correccion":
        sistema.append(PROMPT_CORRECCION)
    if es_demanda:
        sistema.append(PROMPT_DEMANDA)
    mensajes = [{"role": "system", "content": "\n\n".join(sistema)}]

    fund = fundamento(servicio, work.notes, pedido, excluir=excluidos,
                      tipo_escrito="demanda" if es_demanda else detectar_tipo(pedido))
    if fund and fund.texto:
        mensajes.append({"role": "system", "content": "FUNDAMENTO LEGAL DISPONIBLE:\n\n" + fund.texto})

    partes = []
    if modo == "consulta":
        recientes = historial[-6:]
        if recientes:
            partes.append(
                "CONVERSACION RECIENTE DE ESTE CASO:\n"
                + "\n\n".join(
                    f"{'ABOGADA' if m.role == 'user' else 'ASISTENTE'}: {m.content[:2500]}" for m in recientes
                )
            )
        partes.append(_datos_del_caso(session, work, chat_datos))
        partes.append("PREGUNTA DE LA ABOGADA:\n" + pedido)
    elif modo == "nuevo":
        busqueda = f"{servicio or ''} {pedido}".strip()
        ejemplos = get_style_examples(busqueda, pedido=pedido)
        if ejemplos:
            partes.append(
                "Este es un escrito real del despacho, de OTRO caso (ya sin los "
                "nombres de las partes), como MODELO de formato, estilo y fórmulas. "
                "No copies sus datos, sus hechos ni sus artículos:\n\n"
                "<<<MODELO\n" + ejemplos[0] + "\nMODELO>>>"
            )
        anteriores = [m.content for m in historial if m.role == "user"][-6:]
        if anteriores:
            partes.append(
                "Lo que la abogada ya dijo antes en este chat (úsalo si sirve):\n- "
                + "\n- ".join(anteriores)
            )
        partes.append(_datos_del_caso(session, work, chat_datos))
        partes.append("PEDIDO DE LA ABOGADA:\n" + pedido)
    else:
        partes.append("ESCRITO ACTUAL:\n<<<ESCRITO\n" + ultimo_escrito + "\nESCRITO>>>")
        partes.append(_datos_del_caso(session, work, chat_datos))
        partes.append(
            "INDICACIONES DE LA ABOGADA (aplica todas y solo estas; devuelve el "
            "escrito COMPLETO corregido):\n" + pedido
        )
    mensajes.append({"role": "user", "content": "\n\n".join(partes)})
    extras = {
        # numeros de expediente que SI dio la abogada (notas o chat)
        "expedientes": set(re.findall(r"\b\d{1,5}/\d{2,4}\b", (work.notes or "") + " " + " ".join(del_usuario))),
        "lineas_derecho": lineas_de_derecho(fund.citas) if fund else [],
        "excluidos": excluidos,
        **chat_datos,
    }
    return mensajes, modo, extras


def generar_respuesta(session: Session, work: Work, pedido: str) -> tuple[str, str]:
    """Contesta a la abogada. Regresa (texto, tipo) con tipo "escrito" o
    "consulta". Algunas correcciones las hace la app sin el modelo (al
    instante); lo que escribe el modelo se revisa con reglas fijas."""
    historial = session.exec(
        select(WorkMessage).where(WorkMessage.work_id == work.id).order_by(WorkMessage.created_at)
    ).all()
    ultimo_escrito = next(
        (m.content for m in reversed(historial) if m.role == "assistant" and m.tipo == "escrito"), None
    )
    # "EL 1 CAMBIA POR EL 3": se intercambian los hechos directamente.
    if ultimo_escrito:
        cambiado = aplicar_cambio_de_orden(ultimo_escrito, pedido)
        if cambiado:
            return cambiado, "escrito"

    mensajes, modo, extras = _armar_mensajes(session, work, pedido)
    if modo == "consulta":
        texto = chat(mensajes, temperatura=0.2)
        client = session.get(Client, work.client_id)
        return (corregir_nombre(texto, client.name) if client else texto), "consulta"
    texto = chat(mensajes, temperatura=0.15 if modo == "correccion" else None)
    return revisar(session, work, texto, extras), "escrito"


def revisar(session: Session, work: Work, texto: str, extras: dict) -> str:
    """Lo que el modelo hace mal seguido y se puede arreglar sin el modelo.
    Lo que la abogada pidio en el chat (extras) manda sobre lo automatico."""
    client = session.get(Client, work.client_id)
    service = session.get(Service, work.service_id)
    es_sucesorio = bool(service and "sucesori" in _clave(service.name))
    texto = reacomodar_renglones(texto)
    texto = separar_firma(texto)
    texto = arreglar_rubro(texto, es_sucesorio, client.name if client else "")
    texto = renumerar_hechos(texto)
    texto = quitar_bajo_la_clave(texto)
    texto = quitar_expediente_inventado(texto, extras.get("expedientes", set()))
    texto = poner_juzgado(texto, extras.get("juzgado"))
    texto = poner_domicilio(texto, (client.address if client else None) or extras.get("domicilio"))
    texto = poner_lineas_de_derecho(texto, extras.get("lineas_derecho", []))
    texto = quitar_articulos(texto, extras.get("excluidos", set()))
    texto = corregir_fecha(texto)
    if client:
        texto = corregir_nombre(texto, client.name)
        texto = ajustar_genero(texto, client.name)
    return texto


@router.get("/", response_model=List[WorkMessage])
def list_messages(work_id: int, session: Session = Depends(get_session)):
    _load_work_or_404(session, work_id)
    return session.exec(
        select(WorkMessage)
        .where(WorkMessage.work_id == work_id)
        .order_by(WorkMessage.created_at)
    ).all()


@router.post("/", response_model=WorkMessage)
def send_message(
    work_id: int, payload: MessageIn, session: Session = Depends(get_session)
):
    work = _load_work_or_404(session, work_id)

    # Se arma ANTES de guardar el mensaje, para que "el ultimo escrito" y "lo
    # que dijo antes" no incluyan este mismo mensaje.
    reply_text, tipo = generar_respuesta(session, work, payload.content)

    session.add(WorkMessage(work_id=work_id, role="user", content=payload.content))
    assistant_msg = WorkMessage(work_id=work_id, role="assistant", content=reply_text, tipo=tipo)
    session.add(assistant_msg)
    session.commit()
    session.refresh(assistant_msg)
    return assistant_msg


class EdicionIn(BaseModel):
    content: str


@router.put("/{message_id}", response_model=WorkMessage)
def editar_escrito(
    work_id: int, message_id: int, payload: EdicionIn, session: Session = Depends(get_session)
):
    """La abogada corrige el escrito a mano en la app (mas rapido y seguro que
    pedirle cambios chicos al modelo). Si despues pide cambios por el chat, el
    modo corregir parte de ESTE texto editado (es el ultimo del asistente)."""
    msg = session.get(WorkMessage, message_id)
    if not msg or msg.work_id != work_id:
        raise HTTPException(status_code=404, detail="Escrito no encontrado en este caso")
    if msg.role != "assistant":
        raise HTTPException(status_code=400, detail="Solo se pueden editar los escritos del asistente")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="El escrito no puede quedar vacío")
    msg.content = payload.content.rstrip()
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg
