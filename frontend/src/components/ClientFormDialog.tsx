import { useState, type FormEvent, type ReactElement } from 'react'
import { toast } from 'sonner'

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
import { Textarea } from '@/components/ui/textarea'
import { api, type Client } from '@/lib/api'

export function ClientFormDialog({
  client,
  trigger,
  onSaved,
}: {
  client?: Client
  trigger: ReactElement
  onSaved: (c: Client) => void
}) {
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    // Este dialogo puede abrirse dentro de "Nuevo caso"; sin esto el submit
    // sube (por el arbol de React) al formulario del caso y lo crearia antes.
    e.stopPropagation()
    const form = new FormData(e.currentTarget)
    const data = {
      name: String(form.get('name')).trim(),
      email: String(form.get('email')).trim() || null,
      phone: String(form.get('phone')).trim() || null,
      address: String(form.get('address')).trim() || null,
    }
    setSaving(true)
    try {
      const saved = client
        ? await api.clients.update(client.id, data)
        : await api.clients.create(data)
      toast.success(client ? 'Cliente actualizado' : 'Cliente creado')
      setOpen(false)
      onSaved(saved)
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
          <DialogTitle>{client ? 'Editar cliente' : 'Nuevo cliente'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="grid gap-4">
          <Field label="Nombre completo">
            <Input name="name" required defaultValue={client?.name} autoFocus />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Teléfono">
              <Input name="phone" defaultValue={client?.phone ?? ''} />
            </Field>
            <Field label="Correo">
              <Input name="email" type="email" defaultValue={client?.email ?? ''} />
            </Field>
          </div>
          <Field label="Domicilio">
            <Textarea name="address" rows={2} defaultValue={client?.address ?? ''} />
          </Field>
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
