"""
Resumen de lo que cambio entre dos versiones de un escrito, para que J.U.L.I.A.
se lo lea a la Lic. en voz alta despues de cada actualizacion ("Hice 2
cambios. En los hechos: ...").

Se calcula comparando renglon por renglon (sin el modelo): es instantaneo y
no inventa cambios que no hizo.
"""

import difflib
import re

_SECCIONES = [
    (re.compile(r"^\s*P\s*R\s*E\s*S\s*E\s*N\s*T\s*E", re.I), "el proemio"),
    (re.compile(r"^\s*P\s*R\s*E\s*S\s*T\s*A\s*C", re.I), "las prestaciones"),
    (re.compile(r"^\s*H\s*E\s*C\s*H\s*O\s*S", re.I), "los hechos"),
    (re.compile(r"^\s*D\s*E\s*R\s*E\s*C\s*H\s*O", re.I), "el derecho"),
    (re.compile(r"^\s*P\s*R\s*U\s*E\s*B\s*A\s*S", re.I), "las pruebas"),
    (re.compile(r"^\s*(Por lo (anteriormente )?expuesto|En m[ée]rito)", re.I), "los puntos petitorios"),
    (re.compile(r"^\s*P\s*R\s*O\s*T\s*E\s*S\s*T\s*O", re.I), "la firma"),
]


def _con_seccion(texto: str) -> list[tuple[str, str]]:
    """[(seccion, renglon)] -- cada renglon con la seccion a la que pertenece."""
    seccion = "el encabezado"
    out = []
    for r in texto.splitlines():
        if not r.strip():
            continue
        for patron, nombre in _SECCIONES:
            if patron.match(r):
                seccion = nombre
                break
        out.append((seccion, " ".join(r.split())))
    return out


def _corto(r: str, n: int = 260) -> str:
    return r if len(r) <= n else r[:n].rsplit(" ", 1)[0] + "…"


def resumir_cambios(antes: str | None, despues: str) -> str:
    if not antes:
        return "Listo, ya tienes el primer borrador del escrito. Revísalo y dime qué corregimos."
    a, b = _con_seccion(antes), _con_seccion(despues)
    sm = difflib.SequenceMatcher(None, [r for _, r in a], [r for _, r in b], autojunk=False)
    cambios: list[str] = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        seccion = (b[j1][0] if j1 < len(b) else a[i1][0]) if op != "delete" else a[i1][0]
        if op == "delete":
            for _, r in a[i1:i2]:
                cambios.append(f"En {seccion} quité: {_corto(r)}")
        elif op == "insert":
            for _, r in b[j1:j2]:
                cambios.append(f"En {seccion} agregué: {_corto(r)}")
        else:  # replace
            for _, r in b[j1:j2]:
                cambios.append(f"En {seccion} ahora dice: {_corto(r)}")
    if not cambios:
        return "No encontré cambios en el escrito. ¿Me repites qué quieres corregir?"
    if len(cambios) > 8:
        resto = len(cambios) - 6
        cambios = cambios[:6] + [f"y {resto} cambios más que puedes ver en pantalla"]
    n = len(cambios) if len(cambios) <= 8 else "varios"
    return f"Hice {n} {'cambio' if n == 1 else 'cambios'}. " + ". ".join(c.rstrip('.') for c in cambios) + "."


def extraer_seccion(texto: str, seccion: str) -> str:
    """Solo una parte del escrito, para el comando de voz "leeme los hechos".
    `seccion` es como en _SECCIONES: "los hechos", "el derecho", ..."""
    renglones = [r for s, r in _con_seccion(texto) if s == seccion]
    if not renglones:
        return f"No encontré {seccion} en el escrito."
    return "\n".join(renglones)
