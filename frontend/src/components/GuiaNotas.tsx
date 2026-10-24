import { ListChecksIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { guiaDelServicio, plantillaDeNotas } from '@/lib/guias'

// Recuadro "Lo que necesita el asistente" que va junto a las notas del caso,
// segun el servicio elegido.
export function GuiaNotas({
  servicio,
  notas,
  onUsarPlantilla,
}: {
  servicio?: string | null
  notas: string
  onUsarPlantilla: (texto: string) => void
}) {
  const guia = guiaDelServicio(servicio)

  function usar() {
    const plantilla = plantillaDeNotas(guia)
    // Si ya escribio algo, la plantilla se agrega abajo sin borrarlo.
    onUsarPlantilla(notas.trim() ? `${notas.trimEnd()}\n\n${plantilla}` : plantilla)
  }

  return (
    <div className="rounded-lg border border-dashed bg-muted/40 p-3 text-xs">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 font-medium text-foreground">
          <ListChecksIcon className="size-3.5" />
          Lo que necesita J.U.L.I.A.{servicio ? ` para «${servicio}»` : ''}
        </span>
        <Button type="button" variant="outline" size="xs" onClick={usar}>
          Usar plantilla
        </Button>
      </div>
      <ul className="list-disc space-y-0.5 pl-4 text-muted-foreground">
        {guia.map((g) => (
          <li key={g}>{g}</li>
        ))}
      </ul>
    </div>
  )
}
