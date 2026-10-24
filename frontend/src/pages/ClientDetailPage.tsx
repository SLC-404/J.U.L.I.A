import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftIcon, MailIcon, MapPinIcon, PencilIcon, PhoneIcon, PlusIcon } from 'lucide-react'

import { ClientFormDialog } from '@/components/ClientFormDialog'
import { NewWorkDialog } from '@/components/NewWorkDialog'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api, money, shortDate } from '@/lib/api'
import { useData } from '@/lib/use-data'

export default function ClientDetailPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const client = useData(() => api.clients.get(id), [id])
  const works = useData(() => api.works.list(id), [id])
  const services = useData(api.services.list)

  const serviceName = (sid: number) =>
    services.data?.find((s) => s.id === sid)?.name ?? `Servicio #${sid}`

  if (client.error) {
    return <p className="p-8 text-sm text-destructive">{client.error}</p>
  }
  const c = client.data

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link to="/clientes" className="text-muted-foreground hover:text-foreground">
              <ArrowLeftIcon className="size-5" />
            </Link>
            {c?.name ?? '…'}
          </span>
        }
        actions={
          c && (
            <>
              <ClientFormDialog
                client={c}
                onSaved={(updated) => client.setData(updated)}
                trigger={
                  <Button variant="outline">
                    <PencilIcon /> Editar
                  </Button>
                }
              />
              <NewWorkDialog
                clientId={id}
                trigger={
                  <Button>
                    <PlusIcon /> Nuevo caso
                  </Button>
                }
              />
            </>
          )
        }
      />

      {c && (
        <div className="flex flex-wrap gap-x-8 gap-y-2 border-b px-8 py-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <PhoneIcon className="size-4" /> {c.phone ?? 'Sin teléfono'}
          </span>
          <span className="flex items-center gap-1.5">
            <MailIcon className="size-4" /> {c.email ?? 'Sin correo'}
          </span>
          <span className="flex items-center gap-1.5">
            <MapPinIcon className="size-4" /> {c.address ?? 'Sin domicilio'}
          </span>
        </div>
      )}

      <div className="px-8 py-6">
        <h2 className="mb-3 font-medium">Casos</h2>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Servicio</TableHead>
                <TableHead>Inicio</TableHead>
                <TableHead className="text-right">Precio acordado</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(works.data ?? []).map((w) => (
                <TableRow
                  key={w.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/casos/${w.id}`)}
                >
                  <TableCell className="font-medium">{serviceName(w.service_id)}</TableCell>
                  <TableCell>{shortDate(w.started_at ?? w.created_at)}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(w.price)}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{w.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
              {!works.loading && works.data?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                    Este cliente todavía no tiene casos.
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
