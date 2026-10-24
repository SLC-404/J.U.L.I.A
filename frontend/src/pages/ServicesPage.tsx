import { useState, type FormEvent, type ReactElement } from 'react'
import { PencilIcon, PlusIcon } from 'lucide-react'
import { toast } from 'sonner'

import { Field, PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api, money, type Service } from '@/lib/api'
import { useData } from '@/lib/use-data'

function ServiceFormDialog({
  service,
  trigger,
  onSaved,
}: {
  service?: Service
  trigger: ReactElement
  onSaved: () => void
}) {
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const data = {
      name: String(form.get('name')).trim(),
      price: Number(form.get('price')),
      status: form.get('inactive') ? 'inactivo' : 'activo',
    }
    setSaving(true)
    try {
      if (service) await api.services.update(service.id, data)
      else await api.services.create(data)
      toast.success(service ? 'Servicio actualizado' : 'Servicio creado')
      setOpen(false)
      onSaved()
    } catch (err) {
      toast.error(`No se pudo guardar: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{service ? 'Editar servicio' : 'Nuevo servicio'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="grid gap-4">
          <Field label="Nombre del servicio">
            <Input
              name="name"
              required
              autoFocus
              defaultValue={service?.name}
              placeholder="Ej. Demanda de desahucio"
            />
          </Field>
          <Field label="Precio de lista (MXN)">
            <Input
              name="price"
              type="number"
              min={0}
              step="0.01"
              required
              defaultValue={service?.price}
            />
          </Field>
          {service && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                name="inactive"
                defaultChecked={service.status !== 'activo'}
              />
              Ya no se ofrece (ocultarlo al crear casos nuevos)
            </label>
          )}
          <DialogFooter>
            <Button type="submit" disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function ServicesPage() {
  const { data: services, error, loading, reload } = useData(api.services.list)

  return (
    <>
      <PageHeader
        title="Servicios"
        description="Catálogo de servicios del despacho y su precio de lista."
        actions={
          <ServiceFormDialog
            trigger={
              <Button>
                <PlusIcon /> Nuevo servicio
              </Button>
            }
            onSaved={reload}
          />
        }
      />
      <div className="px-8 py-6">
        {error && <p className="mb-4 text-sm text-destructive">No se pudo cargar: {error}</p>}
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Servicio</TableHead>
                <TableHead className="text-right">Precio de lista</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(services ?? []).map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(s.price)}</TableCell>
                  <TableCell>
                    <Badge variant={s.status === 'activo' ? 'secondary' : 'outline'}>
                      {s.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <ServiceFormDialog
                      service={s}
                      onSaved={reload}
                      trigger={
                        <Button variant="ghost" size="icon-sm" aria-label="Editar">
                          <PencilIcon />
                        </Button>
                      }
                    />
                  </TableCell>
                </TableRow>
              ))}
              {!loading && services?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                    Todavía no hay servicios. Crea el primero para poder abrir casos.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </>
  )
}
