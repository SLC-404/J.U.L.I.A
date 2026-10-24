import { useState } from 'react'
import { FileTextIcon, PencilIcon, SaveIcon } from 'lucide-react'
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
import { api, type WorkMessage } from '@/lib/api'

// La Lic. corrige el escrito a mano, como en Word, y lo exporta. Para cambios
// chicos es mas rapido y seguro que pedirselos al asistente por el chat.
export function EditarEscrito({
  workId,
  message,
  onSaved,
  onExport,
}: {
  workId: number
  message: WorkMessage
  onSaved: (m: WorkMessage) => void
  onExport: (m: WorkMessage) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [texto, setTexto] = useState(message.content)
  const [saving, setSaving] = useState(false)
  const cambio = texto !== message.content

  function abrirOCerrar(o: boolean) {
    if (!o && cambio && !window.confirm('Tienes cambios sin guardar. ¿Cerrar y perderlos?')) return
    if (o) setTexto(message.content)
    setOpen(o)
  }

  async function guardar(exportar: boolean) {
    setSaving(true)
    try {
      const guardado = cambio ? await api.messages.update(workId, message.id, texto) : message
      if (cambio) {
        onSaved(guardado)
        toast.success('Escrito guardado')
      }
      setOpen(false)
      if (exportar) await onExport(guardado)
    } catch (err) {
      toast.error(`No se pudo guardar: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={abrirOCerrar}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="sm">
            <PencilIcon /> Editar
          </Button>
        }
      />
      <DialogContent className="flex h-[90svh] flex-col sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Editar escrito</DialogTitle>
          <DialogDescription>
            Corrige el texto como en Word. Respeta los renglones: el rubro, “P R E S E N T E:”,
            los títulos y la firma van cada uno en su renglón para que el Word salga con el
            formato del despacho.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          className="min-h-0 flex-1 resize-none font-serif text-[15px] leading-relaxed"
          spellCheck
          lang="es"
          autoFocus
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => guardar(false)} disabled={saving || !cambio}>
            <SaveIcon /> Guardar
          </Button>
          <Button onClick={() => guardar(true)} disabled={saving}>
            <FileTextIcon /> {cambio ? 'Guardar y exportar a Word' : 'Exportar a Word'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
