import { useEffect, useState } from 'react'
import { SaveIcon } from 'lucide-react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import { useData } from '@/lib/use-data'

// Preferencias de redaccion de la Lic. que el asistente sigue SIEMPRE, en
// todos los casos (antes, lo que corregia en un chat se perdia en el
// siguiente caso).
export default function ReglasPage() {
  const { data, error } = useData(api.ajustes.reglas)
  const [reglas, setReglas] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (data) setReglas(data.reglas)
  }, [data])

  async function guardar() {
    setSaving(true)
    try {
      await api.ajustes.guardarReglas(reglas)
      toast.success('Reglas guardadas: J.U.L.I.A. las usará desde el siguiente mensaje')
    } catch (err) {
      toast.error(`No se pudieron guardar: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  const cambio = data !== null && reglas !== data.reglas

  return (
    <>
      <PageHeader
        title="Reglas del despacho"
        description="Cómo quieres que redacte J.U.L.I.A., en todos los casos."
        actions={
          <Button onClick={guardar} disabled={saving || !cambio}>
            <SaveIcon /> {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        }
      />
      <div className="grid max-w-3xl gap-3 px-8 py-6">
        {error && <p className="text-sm text-destructive">No se pudo cargar: {error}</p>}
        <p className="text-sm text-muted-foreground">
          Una regla por renglón. Por ejemplo: palabras que no quieres que use, cómo va tu firma,
          qué abogados autorizas siempre o cómo se llama cada tipo de escrito. Si en un chat
          corriges algo que siempre debería ser así, agrégalo aquí.
        </p>
        <Textarea
          rows={18}
          value={reglas}
          onChange={(e) => setReglas(e.target.value)}
          className="font-mono text-sm leading-relaxed"
        />
      </div>
    </>
  )
}
