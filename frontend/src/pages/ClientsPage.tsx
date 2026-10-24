import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlusIcon, SearchIcon } from 'lucide-react'

import { ClientFormDialog } from '@/components/ClientFormDialog'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api } from '@/lib/api'
import { useData } from '@/lib/use-data'

export default function ClientsPage() {
  const navigate = useNavigate()
  const { data: clients, error, loading } = useData(api.clients.list)
  const [q, setQ] = useState('')

  const filtered = (clients ?? []).filter((c) =>
    c.name.toLowerCase().includes(q.trim().toLowerCase()),
  )

  return (
    <>
      <PageHeader
        title="Clientes"
        description="Elige un cliente para ver sus casos."
        actions={
          <ClientFormDialog
            trigger={
              <Button>
                <PlusIcon /> Nuevo cliente
              </Button>
            }
            onSaved={(c) => navigate(`/clientes/${c.id}`)}
          />
        }
      />
      <div className="grid gap-4 px-8 py-6">
        <div className="relative max-w-sm">
          <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre…"
            className="pl-8"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>

        {error && <p className="text-sm text-destructive">No se pudo cargar: {error}</p>}

        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Teléfono</TableHead>
                <TableHead>Correo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((c) => (
                <TableRow
                  key={c.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/clientes/${c.id}`)}
                >
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell>{c.phone ?? '—'}</TableCell>
                  <TableCell>{c.email ?? '—'}</TableCell>
                </TableRow>
              ))}
              {!loading && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="py-8 text-center text-muted-foreground">
                    {q ? 'Ningún cliente coincide con la búsqueda.' : 'Todavía no hay clientes.'}
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
