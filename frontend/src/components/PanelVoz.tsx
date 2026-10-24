import { useEffect, useRef, useState } from 'react'
import { Loader2Icon, MicIcon, MicOffIcon, SendIcon, Trash2Icon, Volume2Icon } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { detectarComando, type Comando } from '@/lib/comandos'
import { Microfono, precargarVoz, transcribir, type EstadoMic } from '@/lib/voz'

// Modo "Asistente de voz": el microfono escucha SIEMPRE y lo que dice la Lic.
// se va escribiendo en "Correcciones dictadas" (lo puede corregir a mano).
// Nada se manda a J.U.L.I.A. hasta que da clic en "Enviar actualizacion" (o
// dice "envia la actualizacion"). Las frases que son comandos ("leeme los
// hechos", "repite"...) no se escriben: se ejecutan (ver lib/comandos.ts).
export function PanelVoz({
  workId,
  enviando,
  hablando,
  onEnviar,
  onComando,
}: {
  workId: number
  enviando: boolean // J.U.L.I.A. esta redactando
  hablando: boolean // J.U.L.I.A. esta leyendo en voz alta (el micro se pausa)
  onEnviar: (texto: string) => Promise<boolean>
  onComando: (c: Comando) => Promise<void> // los que no son de este panel
}) {
  const [dictado, setDictado] = useState('')
  const [estado, setEstado] = useState<EstadoMic>('apagado')
  const [nivel, setNivel] = useState(0)
  const [pendientes, setPendientes] = useState(0) // frases transcribiendose
  const [pausaManual, setPausaManual] = useState(false)
  const mic = useRef<Microfono | null>(null)
  // El microfono se arma una sola vez; estas referencias le dan siempre la
  // version actual de las funciones (si no, enviaria un dictado viejo).
  const alComando = useRef<(c: Comando) => void>(() => {})

  useEffect(() => {
    precargarVoz()
    const m = new Microfono({
      onNivel: setNivel,
      onEstado: setEstado,
      onFrase: async (wav) => {
        setPendientes((n) => n + 1)
        try {
          const texto = await transcribir(wav, workId)
          const comando = texto ? detectarComando(texto) : null
          if (comando) alComando.current(comando)
          else if (texto) setDictado((d) => (d.trim() ? `${d.trimEnd()} ${texto}` : texto))
        } catch (err) {
          toast.error(`No entendí esa parte: ${(err as Error).message}`)
        } finally {
          setPendientes((n) => n - 1)
        }
      },
    })
    mic.current = m
    m.iniciar().catch((err) => {
      setEstado('error')
      toast.error(
        `No pude usar el micrófono: ${(err as Error).message}. Revisa el permiso del navegador.`,
      )
    })
    return () => m.detener()
  }, [workId])

  useEffect(() => {
    mic.current?.pausar(hablando || pausaManual)
  }, [hablando, pausaManual])

  async function enviar() {
    const texto = dictado.trim()
    if (!texto) return
    const ok = await onEnviar(texto)
    // Solo se quita lo que se envio: lo que dicto mientras J.U.L.I.A.
    // trabajaba se queda para la siguiente actualizacion.
    if (ok) setDictado((d) => (d.trim().startsWith(texto) ? d.trim().slice(texto.length).trim() : d))
  }

  alComando.current = (c: Comando) => {
    toast.info(`Comando: ${NOMBRES[c.tipo]}${c.tipo === 'seccion' ? ` ${c.seccion}` : ''}`)
    if (c.tipo === 'enviar') {
      if (!dictado.trim()) toast.warning('Todavía no hay correcciones dictadas para enviar.')
      else if (!enviando) void enviar()
    } else if (c.tipo === 'borrar') setDictado('')
    else void onComando(c)
  }

  const etiqueta =
    estado === 'error'
      ? 'Micrófono no disponible'
      : hablando
        ? 'J.U.L.I.A. está hablando…'
        : pausaManual
          ? 'Micrófono en pausa'
          : estado === 'hablando-ella'
            ? 'Te escucho…'
            : pendientes > 0
              ? 'Escribiendo lo que dijiste…'
              : 'Escuchando. Dime las correcciones.'

  return (
    <div className="mx-auto grid max-w-3xl gap-2">
      <div className="flex items-center gap-3 text-sm">
        <span
          className={cn(
            'flex size-8 shrink-0 items-center justify-center rounded-full',
            estado === 'hablando-ella' ? 'bg-red-500 text-white' : 'bg-muted text-muted-foreground',
          )}
        >
          {hablando ? (
            <Volume2Icon className="size-4" />
          ) : pausaManual || estado === 'error' ? (
            <MicOffIcon className="size-4" />
          ) : (
            <MicIcon className="size-4" />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-medium">{etiqueta}</p>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-muted">
            <div
              className="h-full bg-primary transition-[width] duration-75"
              style={{ width: `${pausaManual || hablando ? 0 : Math.round(nivel * 100)}%` }}
            />
          </div>
        </div>
        {pendientes > 0 && <Loader2Icon className="size-4 animate-spin text-muted-foreground" />}
        <Button variant="outline" size="sm" onClick={() => setPausaManual((p) => !p)}>
          {pausaManual ? <MicIcon /> : <MicOffIcon />}
          {pausaManual ? 'Reanudar' : 'Pausar'}
        </Button>
      </div>

      <Textarea
        rows={3}
        value={dictado}
        onChange={(e) => setDictado(e.target.value)}
        placeholder="Aquí aparece lo que vas diciendo. Puedes corregirlo con el teclado antes de enviarlo. Di «¿qué puedo decir?» para oír los comandos."
        className="max-h-48 resize-none"
      />

      <div className="flex items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={() => setDictado('')} disabled={!dictado}>
          <Trash2Icon /> Borrar
        </Button>
        <Button onClick={enviar} disabled={enviando || pendientes > 0 || !dictado.trim()} size="lg">
          {enviando ? <Loader2Icon className="animate-spin" /> : <SendIcon />}
          {enviando ? 'J.U.L.I.A. está trabajando…' : 'Enviar actualización'}
        </Button>
      </div>
    </div>
  )
}

const NOMBRES: Record<Comando['tipo'], string> = {
  seccion: 'leer',
  todo: 'leer todo el escrito',
  cambios: 'leer los cambios',
  repetir: 'repetir',
  enviar: 'enviar actualización',
  borrar: 'borrar lo dictado',
  exportar: 'pasar a Word',
  ayuda: 'ayuda',
}
