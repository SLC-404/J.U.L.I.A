import { useState } from 'react'
import { BookmarkPlusIcon } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'

// Convierte una correccion del chat en regla permanente del despacho: asi lo
// que la Lic. corrige en un caso lo sabe el asistente en todos los demas.
export function GuardarRegla({ texto }: { texto: string }) {
  const [open, setOpen] = useState(false)
  const [regla, setRegla] = useState(texto)
  const [saving, setSaving] = useState(false)

  async function guardar() {
    const nueva = regla.trim()
    if (!nueva) return
    setSaving(true)
    try {
      const { reglas } = await api.ajustes.reglas()
      const numero = (reglas.match(/^\s*\d+\./gm)?.length ?? 0) + 1
      await api.ajustes.guardarReglas(`${reglas.trimEnd()}\n${numero}. ${nueva.replace(/\s+/g, ' ')}\n`)
      toast.success('Regla guardada: J.U.L.I.A. la seguirá en todos los casos')
      setOpen(false)
    } catch (err) {
      toast.error(`No se pudo guardar: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (o) setRegla(texto)
        setOpen(o)
      }}
    >
      <DialogTrigger
        render={
          <button
            type="button"
            className="mt-1 flex items-center gap-1 text-xs text-primary-foreground/70 hover:text-primary-foreground"
          >
            <BookmarkPlusIcon className="size-3" /> Guardar como regla
          </button>
        }
      />
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Guardar como regla del despacho</DialogTitle>
          <DialogDescription>
            Escríbela como algo que debe hacerse SIEMPRE, en cualquier caso. Ej. “En los hechos no
            pongas la fecha de defunción si no viene en las notas”.
          </DialogDescription>
        </DialogHeader>
        <Textarea rows={6} value={regla} onChange={(e) => setRegla(e.target.value)} autoFocus />
        <DialogFooter>
          <Button onClick={guardar} disabled={saving || !regla.trim()}>
            <BookmarkPlusIcon /> Agregar a las reglas
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
