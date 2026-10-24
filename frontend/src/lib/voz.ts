// Microfono que escucha siempre (mientras el modo voz este activo) y corta el
// audio en frases: cuando la Lic. deja de hablar ~1 segundo, esa frase se
// manda a Whisper (en el servidor local) y el texto se agrega a sus
// "correcciones dictadas". No usa servicios de internet.
//
// Funciona en Chrome, Edge y Safari, en Mac y Windows (localhost cuenta como
// sitio seguro, asi que el navegador si deja usar el microfono).

export type EstadoMic = 'apagado' | 'escuchando' | 'hablando-ella' | 'pausado' | 'error'

type Opciones = {
  onFrase: (wav: Blob) => void // una frase lista para transcribir
  onNivel?: (nivel: number) => void // 0..1, para el medidor
  onEstado?: (e: EstadoMic) => void
}

const SR_DESTINO = 16000
const SILENCIO_FIN_MS = 1000 // cuanto silencio cierra una frase
const MIN_FRASE_MS = 400
const MAX_FRASE_MS = 25000
const PREVIO_MS = 300 // lo que se guarda antes de detectar voz (para no cortar la primera silaba)

export class Microfono {
  private ctx: AudioContext | null = null
  private stream: MediaStream | null = null
  private proc: ScriptProcessorNode | null = null
  private pausado = false
  private ruido = 0.008 // piso de ruido (se adapta)
  private enFrase = false
  private trozos: Float32Array[] = []
  private previo: Float32Array[] = []
  private msFrase = 0
  private msSilencio = 0
  private opts: Opciones

  constructor(opts: Opciones) {
    this.opts = opts
  }

  async iniciar() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
    })
    this.ctx = new AudioContext()
    const fuente = this.ctx.createMediaStreamSource(this.stream)
    // ScriptProcessor es viejo pero funciona igual en Chrome, Edge y Safari.
    this.proc = this.ctx.createScriptProcessor(4096, 1, 1)
    this.proc.onaudioprocess = (e) => this.procesar(e.inputBuffer.getChannelData(0))
    fuente.connect(this.proc)
    this.proc.connect(this.ctx.destination)
    this.opts.onEstado?.('escuchando')
  }

  /** Mientras J.U.L.I.A. habla, no se escucha (para no transcribirse a si misma). */
  pausar(si: boolean) {
    this.pausado = si
    if (si) this.descartar()
    this.opts.onEstado?.(si ? 'pausado' : 'escuchando')
  }

  detener() {
    this.proc?.disconnect()
    this.stream?.getTracks().forEach((t) => t.stop())
    this.ctx?.close()
    this.ctx = null
    this.opts.onEstado?.('apagado')
  }

  private descartar() {
    this.enFrase = false
    this.trozos = []
    this.msFrase = 0
    this.msSilencio = 0
  }

  private procesar(muestras: Float32Array) {
    if (!this.ctx) return
    const copia = new Float32Array(muestras)
    const ms = (copia.length / this.ctx.sampleRate) * 1000
    let suma = 0
    for (let i = 0; i < copia.length; i++) suma += copia[i] * copia[i]
    const rms = Math.sqrt(suma / copia.length)
    this.opts.onNivel?.(Math.min(1, rms * 12))
    if (this.pausado) return

    const umbral = Math.max(0.012, this.ruido * 3)
    const hayVoz = rms > umbral
    if (!this.enFrase) {
      // el piso de ruido se ajusta solo cuando no hay voz
      this.ruido = this.ruido * 0.95 + rms * 0.05
      this.previo.push(copia)
      let total = 0
      for (const p of this.previo) total += (p.length / this.ctx.sampleRate) * 1000
      while (total > PREVIO_MS && this.previo.length > 1) {
        total -= (this.previo[0].length / this.ctx.sampleRate) * 1000
        this.previo.shift()
      }
      if (hayVoz) {
        this.enFrase = true
        this.trozos = [...this.previo]
        this.previo = []
        this.msFrase = 0
        this.msSilencio = 0
        this.opts.onEstado?.('hablando-ella')
      }
      return
    }

    this.trozos.push(copia)
    this.msFrase += ms
    this.msSilencio = hayVoz ? 0 : this.msSilencio + ms
    if (this.msSilencio >= SILENCIO_FIN_MS || this.msFrase >= MAX_FRASE_MS) {
      const largo = this.msFrase - this.msSilencio
      const trozos = this.trozos
      this.descartar()
      this.opts.onEstado?.('escuchando')
      if (largo >= MIN_FRASE_MS) this.opts.onFrase(aWav(trozos, this.ctx.sampleRate))
    }
  }
}

/** Junta los trozos, baja a 16 kHz y arma un WAV de 16 bits (lo que espera Whisper). */
function aWav(trozos: Float32Array[], sr: number): Blob {
  const total = trozos.reduce((n, t) => n + t.length, 0)
  const todo = new Float32Array(total)
  let o = 0
  for (const t of trozos) {
    todo.set(t, o)
    o += t.length
  }
  const factor = sr / SR_DESTINO
  const n = Math.floor(todo.length / factor)
  const pcm = new Int16Array(n)
  for (let i = 0; i < n; i++) {
    const v = Math.max(-1, Math.min(1, todo[Math.floor(i * factor)]))
    pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff
  }
  const buf = new ArrayBuffer(44 + pcm.length * 2)
  const d = new DataView(buf)
  const str = (off: number, s: string) => [...s].forEach((c, i) => d.setUint8(off + i, c.charCodeAt(0)))
  str(0, 'RIFF')
  d.setUint32(4, 36 + pcm.length * 2, true)
  str(8, 'WAVE')
  str(12, 'fmt ')
  d.setUint32(16, 16, true)
  d.setUint16(20, 1, true)
  d.setUint16(22, 1, true)
  d.setUint32(24, SR_DESTINO, true)
  d.setUint32(28, SR_DESTINO * 2, true)
  d.setUint16(32, 2, true)
  d.setUint16(34, 16, true)
  str(36, 'data')
  d.setUint32(40, pcm.length * 2, true)
  new Int16Array(buf, 44).set(pcm)
  return new Blob([buf], { type: 'audio/wav' })
}

// --- Voz de J.U.L.I.A. ------------------------------------------------------------

let reproduciendo: HTMLAudioElement | null = null
let terminar: (() => void) | null = null // resuelve la reproduccion en curso si se calla
let turno = 0 // cada decir() nuevo (o callar()) cancela el anterior

/** Parte el texto en frases para que J.U.L.I.A. empiece a hablar con la
 * primera mientras el servidor genera las demas (Chatterbox es lento). La
 * primera es corta para que arranque rapido. */
export function partir(texto: string): string[] {
  const frases = texto
    .split(/(?<=[.!?;:])\s+|\n+/)
    .map((f) => f.trim())
    .filter(Boolean)
  const trozos: string[] = []
  for (let f of frases) {
    // frases muy largas: se cortan en comas o espacios
    while (f.length > 250) {
      let corte = f.lastIndexOf(', ', 250)
      if (corte < 80) corte = f.lastIndexOf(' ', 250)
      if (corte < 1) corte = 250
      trozos.push(f.slice(0, corte + 1).trim())
      f = f.slice(corte + 1).trim()
    }
    const ultimo = trozos[trozos.length - 1]
    const limite = trozos.length === 1 ? 120 : 220
    if (ultimo && ultimo.length + f.length < limite) trozos[trozos.length - 1] = `${ultimo} ${f}`
    else trozos.push(f)
  }
  return trozos
}

async function pedirVoz(texto: string): Promise<Blob> {
  const res = await fetch('/api/voz/hablar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texto }),
  })
  if (!res.ok) throw new Error(`No se pudo generar la voz (${res.status})`)
  return res.blob()
}

function reproducir(blob: Blob, alEmpezar?: () => void): Promise<void> {
  const url = URL.createObjectURL(blob)
  const audio = new Audio(url)
  reproduciendo = audio
  return new Promise<void>((resolve) => {
    const fin = () => {
      URL.revokeObjectURL(url)
      if (reproduciendo === audio) reproduciendo = null
      resolve()
    }
    terminar = fin
    audio.onended = fin
    audio.onerror = fin
    alEmpezar?.()
    audio.play().catch(fin)
  })
}

/** Pide al servidor la voz y la reproduce frase por frase. Resuelve al
 * terminar (o al callar). */
export async function decir(texto: string, alEmpezar?: () => void): Promise<void> {
  callar()
  const mio = ++turno
  const trozos = partir(texto)
  if (!trozos.length) return
  let siguiente = pedirVoz(trozos[0])
  for (let i = 0; i < trozos.length; i++) {
    siguiente.catch(() => {}) // si se cancela, que no quede un error suelto
    const blob = await siguiente
    if (mio !== turno) return
    if (i + 1 < trozos.length) siguiente = pedirVoz(trozos[i + 1])
    await reproducir(blob, i === 0 ? alEmpezar : undefined)
    if (mio !== turno) return
  }
}

export function callar() {
  turno++
  reproduciendo?.pause()
  reproduciendo = null
  terminar?.()
  terminar = null
}

/** Al entrar al modo voz: que el servidor vaya cargando los modelos. */
export function precargarVoz() {
  fetch('/api/voz/estado?precargar=true').catch(() => {})
}

export async function transcribir(wav: Blob, workId: number): Promise<string> {
  const res = await fetch(`/api/voz/transcribir?work_id=${workId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'audio/wav' },
    body: wav,
  })
  if (!res.ok) throw new Error(`No se pudo transcribir (${res.status})`)
  return (await res.json()).texto as string
}
