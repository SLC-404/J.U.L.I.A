// Comandos de voz del modo "Asistente de voz". Si lo que dijo la Lic. es
// EXACTAMENTE un comando ("Léeme los hechos", "Repite", "Ya quedó, pásalo a
// Word"), se ejecuta en lugar de agregarse a las correcciones dictadas.
// Solo frases completas: "en los hechos léeme la fecha" NO es comando, es una
// correccion.

export type Comando =
  | { tipo: 'seccion'; seccion: string } // "los hechos", "el derecho"... (como en backend/app/cambios.py)
  | { tipo: 'todo' }
  | { tipo: 'cambios' }
  | { tipo: 'repetir' }
  | { tipo: 'enviar' }
  | { tipo: 'borrar' }
  | { tipo: 'exportar' }
  | { tipo: 'ayuda' }

export const AYUDA =
  'Puedes decirme: léeme los hechos, léeme el derecho, las prestaciones, las pruebas o los puntos petitorios. ' +
  'Léeme todo. Qué cambiaste. Repite. Envía la actualización. Borra lo dictado. ' +
  'Y cuando el escrito esté bien: ya quedó, pásalo a Word.'

const SECCIONES: Record<string, string> = {
  hechos: 'los hechos',
  derecho: 'el derecho',
  prestaciones: 'las prestaciones',
  pruebas: 'las pruebas',
  proemio: 'el proemio',
  encabezado: 'el encabezado',
  rubro: 'el encabezado',
  'puntos petitorios': 'los puntos petitorios',
  petitorios: 'los puntos petitorios',
  firma: 'la firma',
}

function normalizar(texto: string): string {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-zñ0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^(oye )?julia /, '')
    .replace(/ por favor$/, '')
    .replace(/^por favor /, '')
}

// incluye como suele escribirlo Whisper ("Leme")
const LEE = '(lee|leeme|leme|leer|lealo|leemelo|lemelo|dime)'
const WORD = '(word|guord|uord|güord)'

export function detectarComando(texto: string): Comando | null {
  const t = normalizar(texto)
  if (!t || t.split(' ').length > 8) return null

  const sec = t.match(new RegExp(`^${LEE} (los |el |las |la )?(${Object.keys(SECCIONES).join('|')})$`))
  if (sec) return { tipo: 'seccion', seccion: SECCIONES[sec[3]] }
  if (new RegExp(`^${LEE} (todo|todo el escrito|el escrito|el escrito completo|completo)$`).test(t))
    return { tipo: 'todo' }
  if (/^(que (cambiaste|cambio|le cambiaste)|(lee|leeme|dime) (los |que )?cambios)$/.test(t)) return { tipo: 'cambios' }
  if (/^(repite|repitelo|repiteme|repitemelo|otra vez|de nuevo|que dijiste)$/.test(t)) return { tipo: 'repetir' }
  // envi* / mand*: Whisper a veces escribe "Envida" o "Envita"
  if (/^(envi[a-z]*|mand[a-z]*)( la| las| los)? (actualizacion|cambios|correcciones)$/.test(t))
    return { tipo: 'enviar' }
  if (/^(borra|borrar) (lo dictado|todo lo dictado|las correcciones|lo que dije)$/.test(t)) return { tipo: 'borrar' }
  if (new RegExp(`^(ya quedo |ya esta |listo )?(exporta|exportalo|pasa|pasalo|guarda|guardalo|manda|mandalo) (a|al|en) ${WORD}$`).test(t))
    return { tipo: 'exportar' }
  if (/^(que (puedo|te puedo) (decir|pedir)|ayuda|que comandos hay)$/.test(t)) return { tipo: 'ayuda' }
  return null
}
