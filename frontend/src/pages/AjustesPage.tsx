import { useEffect, useState } from 'react'
import { FolderOpenIcon, RotateCcwIcon, SaveIcon, TriangleAlertIcon } from 'lucide-react'
import { toast } from 'sonner'

import { Field, PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api, type Carpetas } from '@/lib/api'
import { useData } from '@/lib/use-data'

// Donde guarda J.U.L.I.A. los archivos (ver backend/app/carpetas.py).
export default function AjustesPage() {
  const { data, error, setData } = useData(api.ajustes.carpetas)
  const [archivos, setArchivos] = useState('')
  const [respaldos, setRespaldos] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (data) {
      setArchivos(data.archivos)
      setRespaldos(data.respaldos)
    }
  }, [data])

  async function guardar() {
    setSaving(true)
    try {
      const nuevas: Carpetas = await api.ajustes.guardarCarpetas({ archivos, respaldos })
      setData(nuevas)
      toast.success('Carpetas guardadas. Los siguientes archivos se guardarán ahí.')
    } catch (err) {
      toast.error((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  async function abrir(cual: 'archivos' | 'respaldos') {
    try {
      await api.ajustes.abrirCarpeta(cual)
    } catch (err) {
      toast.error((err as Error).message)
    }
  }

  const cambio = data !== null && (archivos !== data.archivos || respaldos !== data.respaldos)

  return (
    <>
      <PageHeader
        title="Ajustes"
        description="Dónde guarda J.U.L.I.A. los documentos y los respaldos."
        actions={
          <Button onClick={guardar} disabled={saving || !cambio}>
            <SaveIcon /> {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        }
      />
      <div className="grid max-w-3xl gap-6 px-8 py-6">
        {error && <p className="text-sm text-destructive">No se pudo cargar: {error}</p>}
        {data?.avisos.map((a) => (
          <p key={a} className="flex gap-2 rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
            <TriangleAlertIcon className="size-4 shrink-0 text-amber-600" /> {a}
          </p>
        ))}

        <Carpeta
          titulo="Carpeta de archivos"
          ayuda="Aquí se guardan los Word de cada caso, ordenados así: Casos › Cliente › Servicio (caso N)."
          valor={archivos}
          defecto={data?.por_defecto.archivos}
          onCambiar={setArchivos}
          onAbrir={() => abrir('archivos')}
        />
        <Carpeta
          titulo="Carpeta de respaldos"
          ayuda="Copia diaria de la base de datos y de los documentos (se hace sola al abrir J.U.L.I.A.). Conviene copiarla a una USB de vez en cuando."
          valor={respaldos}
          defecto={data?.por_defecto.respaldos}
          onCambiar={setRespaldos}
          onAbrir={() => abrir('respaldos')}
        />

        <p className="text-xs text-muted-foreground">
          Escribe la ruta completa de la carpeta (por ejemplo C:\Users\Juana\J.U.L.I.A. en Windows). Si no
          existe, se crea. Evita carpetas de OneDrive, iCloud o Google Drive: los datos de los clientes
          saldrían de la computadora. Los archivos que ya existían se quedan donde estaban y se siguen
          pudiendo descargar.
        </p>
      </div>
    </>
  )
}

function Carpeta({
  titulo,
  ayuda,
  valor,
  defecto,
  onCambiar,
  onAbrir,
}: {
  titulo: string
  ayuda: string
  valor: string
  defecto?: string
  onCambiar: (v: string) => void
  onAbrir: () => void
}) {
  return (
    <Field label={titulo}>
      <div className="flex gap-2">
        <Input value={valor} onChange={(e) => onCambiar(e.target.value)} className="font-mono text-sm" />
        <Button variant="outline" onClick={onAbrir} title="Abrir la carpeta">
          <FolderOpenIcon /> Abrir
        </Button>
        {defecto && valor !== defecto && (
          <Button variant="ghost" onClick={() => onCambiar(defecto)} title={`Usar ${defecto}`}>
            <RotateCcwIcon />
          </Button>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{ayuda}</p>
    </Field>
  )
}
