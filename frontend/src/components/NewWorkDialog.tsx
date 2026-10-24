import { useEffect, useState, type FormEvent, type ReactElement } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileTextIcon, MicIcon, UserPlusIcon } from 'lucide-react'
import { toast } from 'sonner'

import { ClientFormDialog } from '@/components/ClientFormDialog'
import { GuiaNotas } from '@/components/GuiaNotas'
import { Field } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { api, type Client, type Service } from '@/lib/api'
import { cn } from '@/lib/utils'

// Dialogo para abrir un caso nuevo. Se usa en dos lugares:
//   - en el detalle de un cliente (clientId fijo), y
//   - como acceso directo en el menu lateral: ahi se elige el cliente o se
//     crea uno nuevo sin salir del dialogo.
// Al crear el caso, lleva directo a su pantalla (chat con el asistente).
export function NewWorkDialog({
  clientId,
  trigger,
}: {
  clientId?: number
  trigger: ReactElement
}) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [clients, setClients] = useState<Client[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [pickedClient, setPickedClient] = useState<string | null>(null)
  const [serviceId, setServiceId] = useState<string | null>(null)
  const [price, setPrice] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [modo, setModo] = useState<'escrito' | 'voz'>('escrito')

  // Cada vez que se abre: datos frescos y formulario limpio.
  useEffect(() => {
    if (!open) return
    setPickedClient(clientId ? String(clientId) : null)
    setServiceId(null)
    setPrice('')
    setNotes('')
    api.services.list().then(setServices).catch(() => setServices([]))
    if (!clientId) api.clients.list().then(setClients).catch(() => setClients([]))
  }, [open, clientId])

  const active = services.filter((s) => s.status === 'activo')

  function pickService(id: string | null) {
    setServiceId(id)
    const s = active.find((x) => String(x.id) === id)
    if (s) setPrice(String(s.price)) // precio de lista como punto de partida
  }

  function onClientCreated(c: Client) {
    setClients((prev) => [...prev, c])
    setPickedClient(String(c.id))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!serviceId || !pickedClient) return
    setSaving(true)
    try {
      const work = await api.works.create({
        client_id: Number(pickedClient),
        service_id: Number(serviceId),
        price: Number(price),
        notes: notes.trim() || null,
        started_at: new Date().toISOString(),
      })
      try {
        localStorage.setItem(`julia-modo-caso-${work.id}`, modo)
      } catch {
        // sin almacenamiento: se elige de nuevo dentro del caso
      }
      toast.success('Caso creado')
      setOpen(false)
      navigate(`/casos/${work.id}`)
    } catch (err) {
      toast.error(`No se pudo crear el caso: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={trigger} />
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Nuevo caso</DialogTitle>
        </DialogHeader>
        {services.length > 0 && active.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Primero da de alta al menos un servicio en{' '}
            <Link to="/servicios" className="underline" onClick={() => setOpen(false)}>
              Servicios
            </Link>
            .
          </p>
        ) : (
          <form onSubmit={onSubmit} className="grid gap-4">
            {!clientId && (
              <Field label="Cliente">
                <div className="flex gap-2">
                  <Select
                    value={pickedClient}
                    onValueChange={(v) => setPickedClient(v as string | null)}
                    items={clients.map((c) => ({ value: String(c.id), label: c.name }))}
                  >
                    <SelectTrigger className="min-w-0 flex-1">
                      <SelectValue placeholder="Elige el cliente" />
                    </SelectTrigger>
                    <SelectContent>
                      {clients.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <ClientFormDialog
                    onSaved={onClientCreated}
                    trigger={
                      <Button type="button" variant="outline">
                        <UserPlusIcon /> Nuevo cliente
                      </Button>
                    }
                  />
                </div>
              </Field>
            )}
            <Field label="Servicio">
              <Select
                value={serviceId}
                onValueChange={(v) => pickService(v as string | null)}
                items={active.map((s) => ({ value: String(s.id), label: s.name }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Elige el servicio" />
                </SelectTrigger>
                <SelectContent>
                  {active.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Precio acordado (MXN)">
              <Input
                type="number"
                min={0}
                step="0.01"
                required
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </Field>
            <Field label="Notas del caso (J.U.L.I.A. las toma en cuenta)">
              <Textarea
                rows={6}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Escribe aquí los datos del caso, o usa la plantilla de abajo."
              />
            </Field>
            <GuiaNotas
              servicio={active.find((s) => String(s.id) === serviceId)?.name}
              notas={notes}
              onUsarPlantilla={setNotes}
            />
            <Field label="¿Cómo quieres trabajar el caso?">
              <div className="grid grid-cols-2 gap-2">
                {(
                  [
                    ['escrito', FileTextIcon, 'Escrito', 'Escribes las correcciones en el chat'],
                    ['voz', MicIcon, 'Asistente de voz', 'Le dices las correcciones y J.U.L.I.A. te lee los cambios'],
                  ] as const
                ).map(([valor, Icono, titulo, desc]) => (
                  <button
                    key={valor}
                    type="button"
                    onClick={() => setModo(valor)}
                    className={cn(
                      'rounded-md border p-3 text-left text-sm transition-colors',
                      modo === valor ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'hover:bg-muted',
                    )}
                  >
                    <span className="flex items-center gap-2 font-medium">
                      <Icono className="size-4" /> {titulo}
                    </span>
                    <span className="mt-1 block text-xs text-muted-foreground">{desc}</span>
                  </button>
                ))}
              </div>
            </Field>
            <DialogFooter>
              <Button type="submit" disabled={saving || !serviceId || !pickedClient}>
                {saving ? 'Creando…' : 'Crear caso'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
