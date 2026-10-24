import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeftIcon,
  DownloadIcon,
  FileTextIcon,
  KeyboardIcon,
  Loader2Icon,
  MicIcon,
  SendIcon,
  SquareIcon,
  Volume2Icon,
} from 'lucide-react'
import { toast } from 'sonner'

import { EditarEscrito } from '@/components/EditarEscrito'
import { GuardarRegla } from '@/components/GuardarRegla'
import { MessageText } from '@/components/MessageText'
import { NotasDelCaso } from '@/components/NotasDelCaso'
import { PageHeader } from '@/components/PageHeader'
import { PanelVoz } from '@/components/PanelVoz'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { api, money, shortDate, type WorkMessage } from '@/lib/api'
import { useData } from '@/lib/use-data'
import { cn } from '@/lib/utils'
import { AYUDA, type Comando } from '@/lib/comandos'
import { callar, decir } from '@/lib/voz'

const STATUSES = [
  { value: 'activo', label: 'Activo' },
  { value: 'en pausa', label: 'En pausa' },
  { value: 'terminado', label: 'Terminado' },
]

export default function WorkPage() {
  const id = Number(useParams().id)
  const work = useData(() => api.works.get(id), [id])
  const client = useData(
    async () => (work.data ? api.clients.get(work.data.client_id) : null),
    [work.data?.client_id],
  )
  const services = useData(api.services.list)
  const messages = useData(() => api.messages.list(id), [id])
  const files = useData(() => api.files.list(id), [id])

  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  // "Escrito" o "Asistente de voz": se recuerda por caso en este navegador.
  const claveModo = `julia-modo-caso-${id}`
  const [modoVoz, setModoVoz] = useState(() => {
    try {
      return localStorage.getItem(claveModo) === 'voz'
    } catch {
      return false
    }
  })
  const [hablando, setHablando] = useState(false)
  const [leyendoId, setLeyendoId] = useState<number | null>(null)
  const turnoVoz = useRef(0) // solo la ultima lectura apaga el "hablando"
  const ultimoDicho = useRef('')

  function cambiarModo(voz: boolean) {
    setModoVoz(voz)
    if (!voz) callar()
    try {
      localStorage.setItem(claveModo, voz ? 'voz' : 'escrito')
    } catch {
      // sin almacenamiento: solo dura esta visita
    }
  }

  async function leer(texto: string, msgId: number | null = null) {
    const turno = ++turnoVoz.current
    ultimoDicho.current = texto
    setLeyendoId(msgId)
    setHablando(true)
    try {
      await decir(texto)
    } catch (err) {
      toast.error(`No pude leerlo en voz alta: ${(err as Error).message}`)
    } finally {
      if (turno === turnoVoz.current) {
        setHablando(false)
        setLeyendoId(null)
      }
    }
  }

  function detenerLectura() {
    turnoVoz.current++
    callar()
    setHablando(false)
    setLeyendoId(null)
  }

  // Despues de cada actualizacion en modo voz: le lee a la Lic. que cambio.
  async function leerCambios(m: WorkMessage) {
    try {
      const { resumen } = await api.messages.cambios(id, m.id)
      await leer(resumen, m.id)
    } catch (err) {
      toast.error(`No pude preparar el resumen: ${(err as Error).message}`)
    }
  }
  const [exportingId, setExportingId] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.data?.length, sending])

  const service = services.data?.find((s) => s.id === work.data?.service_id)

  async function enviarTexto(content: string): Promise<boolean> {
    if (!content || sending) return false
    // Se muestra el mensaje de inmediato; el agente puede tardar un rato.
    const pending: WorkMessage = {
      id: -Date.now(),
      work_id: id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    messages.setData([...(messages.data ?? []), pending])
    setSending(true)
    if (modoVoz) void leer('Va, estoy trabajando en los cambios. Dame un momento.')
    let respuesta: WorkMessage | null = null
    try {
      respuesta = await api.messages.send(id, content)
    } catch (err) {
      toast.error(`J.U.L.I.A. no respondió: ${(err as Error).message}`)
    } finally {
      setSending(false)
      messages.reload()
    }
    if (respuesta && modoVoz) void leerCambios(respuesta)
    return respuesta !== null
  }

  async function send() {
    const content = draft.trim()
    setDraft('')
    const ok = await enviarTexto(content)
    if (!ok) setDraft(content)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  async function exportToWord(m: WorkMessage): Promise<boolean> {
    setExportingId(m.id)
    try {
      const f = await api.files.fromMessage(id, m.id)
      toast.success(
        f.type === 'revisado_lic'
          ? 'Word listo. J.U.L.I.A. aprendió de tu versión para los próximos escritos.'
          : 'Documento de Word listo',
        {
          action: { label: 'Descargar', onClick: () => window.open(api.files.downloadUrl(f.id)) },
        },
      )
      files.reload()
      return true
    } catch (err) {
      toast.error(`No se pudo exportar: ${(err as Error).message}`)
      return false
    } finally {
      setExportingId(null)
    }
  }

  // Comandos de voz (lib/comandos.ts); siempre sobre el ultimo escrito.
  async function ejecutarComando(c: Comando) {
    const escrito = [...(messages.data ?? [])]
      .reverse()
      .find((m) => m.role === 'assistant' && m.tipo !== 'consulta' && m.id > 0)
    if (c.tipo === 'ayuda') return leer(AYUDA)
    if (c.tipo === 'repetir') return leer(ultimoDicho.current || 'Todavía no te he leído nada.')
    if (!escrito) return leer('Todavía no hay un escrito en este caso. Dime qué escrito necesitas y envía la actualización.')
    if (c.tipo === 'todo') return leer(escrito.content, escrito.id)
    if (c.tipo === 'cambios') return leerCambios(escrito)
    if (c.tipo === 'seccion') {
      try {
        const { texto } = await api.messages.seccion(id, escrito.id, c.seccion)
        return leer(texto, escrito.id)
      } catch (err) {
        toast.error(`No pude leer esa parte: ${(err as Error).message}`)
        return
      }
    }
    if (c.tipo === 'exportar') {
      if (await exportToWord(escrito))
        return leer('Listo, ya está en Word. Lo encuentras en Documentos del caso.')
      return leer('No pude pasarlo a Word. Revisa el mensaje en pantalla.')
    }
  }

  async function changeStatus(status: string | null) {
    if (!status || !work.data) return
    try {
      work.setData(await api.works.update(id, { status }))
    } catch (err) {
      toast.error(`No se pudo cambiar el estado: ${(err as Error).message}`)
    }
  }

  if (work.error) return <p className="p-8 text-sm text-destructive">{work.error}</p>

  return (
    <div className="flex h-svh flex-col">
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link
              to={work.data ? `/clientes/${work.data.client_id}` : '/clientes'}
              className="text-muted-foreground hover:text-foreground"
            >
              <ArrowLeftIcon className="size-5" />
            </Link>
            {service?.name ?? 'Caso'}
          </span>
        }
        description={
          work.data && (
            <>
              {client.data?.name ?? '…'} · {money(work.data.price)} · desde{' '}
              {shortDate(work.data.started_at ?? work.data.created_at)}
            </>
          )
        }
        actions={
          work.data && (
            <>
            <Button
              variant={modoVoz ? 'default' : 'outline'}
              onClick={() => cambiarModo(!modoVoz)}
              title={modoVoz ? 'Cambiar a escribir' : 'Hablarle a J.U.L.I.A.'}
            >
              {modoVoz ? <KeyboardIcon /> : <MicIcon />}
              {modoVoz ? 'Escribir' : 'Asistente de voz'}
            </Button>
            <Select value={work.data.status} onValueChange={(v) => changeStatus(v as string | null)} items={STATUSES}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            </>
          )
        }
      />

      <div className="flex min-h-0 flex-1">
        {/* Chat */}
        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-8 py-6">
            <div className="mx-auto grid max-w-3xl gap-4">
              {work.data && (
                <NotasDelCaso
                  work={work.data}
                  servicio={service?.name}
                  onSaved={(w) => work.setData(w)}
                />
              )}

              {messages.data?.length === 0 && !sending && (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Pídele a J.U.L.I.A. el primer borrador (“Redáctame el escrito de apersonamiento”)
                  o hazle una pregunta (“¿Qué plazo tengo para apersonarme?”). Los cambios finos
                  hazlos tú con “Editar”: lo que exportes corregido, J.U.L.I.A. lo aprende.
                </p>
              )}

              {(messages.data ?? []).map((m) => (
                <div
                  key={m.id}
                  className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}
                >
                  <div
                    className={cn(
                      'max-w-[85%] rounded-xl px-4 py-3 text-sm',
                      m.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'border bg-card',
                    )}
                  >
                    {m.role === 'user' ? (
                      <>
                        <p className="whitespace-pre-wrap">{m.content}</p>
                        <GuardarRegla texto={m.content} />
                      </>
                    ) : m.tipo === 'consulta' ? (
                      <>
                        <p className="mb-2 text-xs font-medium text-muted-foreground">
                          Respuesta a tu pregunta
                        </p>
                        <MessageText text={m.content} />
                        <div className="mt-3 border-t pt-2">
                          {leyendoId === m.id ? (
                            <Button variant="ghost" size="sm" onClick={detenerLectura}>
                              <SquareIcon /> Detener
                            </Button>
                          ) : (
                            <Button variant="ghost" size="sm" onClick={() => leer(m.content, m.id)} disabled={hablando}>
                              <Volume2Icon /> Escuchar
                            </Button>
                          )}
                        </div>
                      </>
                    ) : (
                      <>
                        <MessageText text={m.content} />
                        <div className="mt-3 flex flex-wrap items-center gap-1 border-t pt-2">
                          <EditarEscrito
                            workId={id}
                            message={m}
                            onSaved={(nuevo) =>
                              messages.setData(
                                (messages.data ?? []).map((x) => (x.id === nuevo.id ? nuevo : x)),
                              )
                            }
                            onExport={async (m) => void (await exportToWord(m))}
                          />
                          {leyendoId === m.id ? (
                            <Button variant="ghost" size="sm" onClick={detenerLectura}>
                              <SquareIcon /> Detener
                            </Button>
                          ) : (
                            <>
                              <Button variant="ghost" size="sm" onClick={() => leerCambios(m)} disabled={hablando}>
                                <Volume2Icon /> Escuchar cambios
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => leer(m.content, m.id)} disabled={hablando}>
                                <Volume2Icon /> Leer todo
                              </Button>
                            </>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => exportToWord(m)}
                            disabled={exportingId === m.id}
                          >
                            {exportingId === m.id ? (
                              <Loader2Icon className="animate-spin" />
                            ) : (
                              <FileTextIcon />
                            )}
                            Exportar a Word
                          </Button>
                          {m.updated_at && m.updated_at.slice(0, 19) !== m.created_at.slice(0, 19) && (
                            <span className="ml-auto text-xs text-muted-foreground">
                              Editado a mano
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2Icon className="size-4 animate-spin" />
                  J.U.L.I.A. está escribiendo… (puede tardar hasta un minuto)
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="border-t px-8 py-4">
            {modoVoz ? (
              <PanelVoz workId={id} enviando={sending} hablando={hablando} onEnviar={enviarTexto} onComando={ejecutarComando} />
            ) : (
              <div className="mx-auto flex max-w-3xl items-end gap-2">
                <Textarea
                  rows={2}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Escribe tu mensaje… (Enter para enviar, Shift+Enter para salto de línea)"
                  className="max-h-48 resize-none"
                  disabled={sending}
                />
                <Button onClick={send} disabled={sending || !draft.trim()} size="lg">
                  <SendIcon /> Enviar
                </Button>
              </div>
            )}
          </div>
        </section>

        {/* Documentos */}
        <aside className="w-72 shrink-0 overflow-y-auto border-l p-4">
          <h2 className="mb-3 text-sm font-medium">Documentos del caso</h2>
          {files.data?.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Aún no hay documentos. Usa “Exportar a Word” en una respuesta de J.U.L.I.A.
            </p>
          )}
          <ul className="flex flex-col gap-2">
            {(files.data ?? []).map((f) => (
              <li key={f.id}>
                <a
                  href={api.files.downloadUrl(f.id)}
                  className="flex items-start gap-2 rounded-md border p-2 text-sm hover:bg-muted"
                >
                  <DownloadIcon className="mt-0.5 size-4 shrink-0" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{f.filename}</span>
                    <span className="text-xs text-muted-foreground">
                      {shortDate(f.created_at)} · {f.type === 'borrador_ia' ? 'Borrador IA' : f.type === 'revisado_lic' ? 'Revisado por ti ✓' : f.type}
                    </span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  )
}
