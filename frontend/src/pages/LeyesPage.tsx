import { useEffect, useRef } from 'react'
import {
  AlertTriangleIcon,
  CalendarClockIcon,
  CheckCircle2Icon,
  ExternalLinkIcon,
  Loader2Icon,
  RefreshCwIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useData } from '@/lib/use-data'

const fechaHora = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString('es-MX', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'nunca'

export default function LeyesPage() {
  const { data, error, reload } = useData(api.leyes.estado)
  const corriendo = data?.trabajo.corriendo ?? false
  const estabaCorriendo = useRef(false)

  // Mientras se actualiza, se pregunta el avance cada 2 segundos.
  useEffect(() => {
    if (!corriendo) return
    const t = setInterval(reload, 2000)
    return () => clearInterval(t)
  }, [corriendo, reload])

  // Al terminar, un aviso con el resultado.
  useEffect(() => {
    if (estabaCorriendo.current && !corriendo && data) {
      const hubo = data.trabajo.resultados.some((r) => r.estado === 'error')
      ;(hubo ? toast.warning : toast.success)(data.trabajo.mensaje)
    }
    estabaCorriendo.current = corriendo
  }, [corriendo, data])

  async function actualizar() {
    try {
      await api.leyes.actualizar()
      reload()
    } catch (err) {
      toast.error(`No se pudo empezar: ${(err as Error).message}`)
    }
  }

  return (
    <>
      <PageHeader
        title="Leyes"
        description="Códigos que consulta J.U.L.I.A. y la fecha de su última reforma."
        actions={
          <Button onClick={actualizar} disabled={corriendo}>
            {corriendo ? <Loader2Icon className="animate-spin" /> : <RefreshCwIcon />}
            {corriendo ? 'Buscando…' : 'Buscar actualizaciones'}
          </Button>
        }
      />
      <div className="grid max-w-3xl gap-4 px-8 py-6">
        {error && <p className="text-sm text-destructive">No se pudo cargar: {error}</p>}

        {data && (
          <div className="flex items-start gap-3 rounded-lg border p-4 text-sm">
            <CalendarClockIcon className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
            <div className="grid gap-1">
              <p className="font-medium">Revisión automática cada mes</p>
              <p className="text-muted-foreground">
                Última:{' '}
                <span className="text-foreground">
                  {fechaHora(data.programacion.ultima_ejecucion)}
                </span>
                {data.programacion.origen &&
                  ` (${data.programacion.origen === 'automatica' ? 'automática' : 'con el botón'})`}
                {' · '}Próxima:{' '}
                <span className="text-foreground">
                  {fechaHora(data.programacion.proxima_ejecucion)}
                </span>
              </p>
              <p className="text-xs text-muted-foreground">
                Se hace sola mientras la app esté abierta. Si ese día la Mac estaba apagada, se
                hace en cuanto se vuelva a abrir. Si falla por falta de internet, se reintenta al
                día siguiente.
              </p>
            </div>
          </div>
        )}

        {data && (corriendo || data.trabajo.fin) && (
          <div className="flex items-start gap-2 rounded-lg border bg-muted/40 p-3 text-sm">
            {corriendo ? (
              <Loader2Icon className="mt-0.5 size-4 shrink-0 animate-spin" />
            ) : (
              <CheckCircle2Icon className="mt-0.5 size-4 shrink-0" />
            )}
            <div>
              <p>{data.trabajo.mensaje}</p>
              {corriendo && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Puedes seguir usando la app mientras tanto. Si se actualiza un código, tarda
                  unos minutos.
                </p>
              )}
            </div>
          </div>
        )}

        {data?.codigos.map((c) => (
          <div key={c.archivo} className="rounded-lg border p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h2 className="font-medium">{c.nombre}</h2>
              <a
                href={c.fuente}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                Fuente oficial <ExternalLinkIcon className="size-3" />
              </a>
            </div>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Última reforma</dt>
              <dd className="font-medium">{c.ultima_reforma ?? 'sin dato (falta revisar)'}</dd>
              <dt className="text-muted-foreground">Revisado</dt>
              <dd>{fechaHora(c.revisado)}</dd>
              <dt className="text-muted-foreground">Actualizado en la app</dt>
              <dd>{fechaHora(c.actualizado)}</dd>
            </dl>
            {c.error && (
              <p className="mt-2 flex items-start gap-1.5 text-xs text-destructive">
                <AlertTriangleIcon className="mt-0.5 size-3.5 shrink-0" />
                Último intento falló: {c.error}. Se sigue usando la versión que ya estaba.
              </p>
            )}
          </div>
        ))}

        <p className="text-xs text-muted-foreground">
          La revisión (automática o con el botón) baja los códigos de su fuente oficial
          (Legislatura del Estado de México y Cámara de Diputados) y solo vuelve a cargar los que
          cambiaron. Aun con la ley al día, revisa los transitorios y la entrada en vigor: el
          asistente no los interpreta.
        </p>
      </div>
    </>
  )
}
