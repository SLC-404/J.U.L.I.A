import { useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/PageHeader'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api, money } from '@/lib/api'
import { useData } from '@/lib/use-data'

export default function ReportsPage() {
  const navigate = useNavigate()
  const { data: rows, error, loading } = useData(api.reports.clients)

  const totalWorks = (rows ?? []).reduce((acc, r) => acc + r.works_count, 0)
  const totalAmount = (rows ?? []).reduce((acc, r) => acc + r.total, 0)

  return (
    <>
      <PageHeader
        title="Reportes"
        description="Por cliente: cuántos casos ha tenido y la suma de lo acordado en ellos."
      />
      <div className="grid gap-6 px-8 py-6">
        <div className="grid max-w-xl grid-cols-2 gap-4">
          <div className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">Casos en total</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{totalWorks}</p>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">Total acordado</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{money(totalAmount)}</p>
          </div>
        </div>

        {error && <p className="text-sm text-destructive">No se pudo cargar: {error}</p>}

        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cliente</TableHead>
                <TableHead className="text-right">Casos</TableHead>
                <TableHead className="text-right">Total acordado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(rows ?? []).map((r) => (
                <TableRow
                  key={r.client_id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/clientes/${r.client_id}`)}
                >
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-right tabular-nums">{r.works_count}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(r.total)}</TableCell>
                </TableRow>
              ))}
              {!loading && rows?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="py-8 text-center text-muted-foreground">
                    Todavía no hay clientes.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
            {rows && rows.length > 0 && (
              <TableFooter>
                <TableRow>
                  <TableCell>Total</TableCell>
                  <TableCell className="text-right tabular-nums">{totalWorks}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(totalAmount)}</TableCell>
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </div>

        <p className="text-xs text-muted-foreground">
          El total es la suma del precio acordado de cada caso. Todavía no se registran pagos,
          así que no distingue lo ya cobrado de lo pendiente.
        </p>
      </div>
    </>
  )
}
