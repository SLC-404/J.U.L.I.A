import { useState } from 'react'
import { PencilIcon } from 'lucide-react'
import { toast } from 'sonner'

import { GuiaNotas } from '@/components/GuiaNotas'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { api, type Work } from '@/lib/api'

// Recuadro de notas arriba del chat del caso, con boton para editarlas (y la
// guia de que datos necesita el asistente para este servicio).
export function NotasDelCaso({
  work,
  servicio,
  onSaved,
}: {
  work: Work
  servicio?: string
  onSaved: (w: Work) => void
}) {
  const [open, setOpen] = useState(false)
  const [notas, setNotas] = useState(work.notes ?? '')
  const [saving, setSaving] = useState(false)

  async function guardar() {
    setSaving(true)
    try {
      onSaved(await api.works.update(work.id, { notes: notas.trim() || null }))
      toast.success('Notas guardadas')
      setOpen(false)
    } catch (err) {
      toast.error(`No se pudieron guardar: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="font-medium text-foreground">Notas del caso</span>
        <Dialog
          open={open}
          onOpenChange={(o) => {
            setOpen(o)
            if (o) setNotas(work.notes ?? '')
          }}
        >
          <DialogTrigger
            render={
              <Button variant="ghost" size="sm">
                <PencilIcon /> {work.notes ? 'Editar' : 'Agregar datos'}
              </Button>
            }
          />
          <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>Notas del caso</DialogTitle>
            </DialogHeader>
            <Textarea
              rows={12}
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Escribe aquí los datos del caso, o usa la plantilla de abajo."
              autoFocus
            />
            <GuiaNotas servicio={servicio} notas={notas} onUsarPlantilla={setNotas} />
            <DialogFooter>
              <Button onClick={guardar} disabled={saving}>
                {saving ? 'Guardando…' : 'Guardar notas'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      {work.notes ? (
        <p className="whitespace-pre-wrap">{work.notes}</p>
      ) : (
        <p>
          Sin notas. Agrega los datos del caso para que J.U.L.I.A. no tenga que dejar huecos
          ni inventar.
        </p>
      )}
    </div>
  )
}
