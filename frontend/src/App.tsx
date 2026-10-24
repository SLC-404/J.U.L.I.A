import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { BarChart3Icon, BookOpenIcon, BriefcaseIcon, FilePlusIcon, ListChecksIcon, ScaleIcon, SettingsIcon, UsersIcon } from 'lucide-react'

import { NewWorkDialog } from '@/components/NewWorkDialog'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Toaster } from '@/components/ui/sonner'
import { cn } from '@/lib/utils'
import AjustesPage from '@/pages/AjustesPage'
import ClientsPage from '@/pages/ClientsPage'
import ClientDetailPage from '@/pages/ClientDetailPage'
import LeyesPage from '@/pages/LeyesPage'
import ReglasPage from '@/pages/ReglasPage'
import ReportsPage from '@/pages/ReportsPage'
import ServicesPage from '@/pages/ServicesPage'
import WorkPage from '@/pages/WorkPage'

function NavItem({ to, icon: Icon, label }: { to: string; icon: typeof UsersIcon; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground',
          isActive && 'bg-muted text-foreground',
        )
      }
    >
      <Icon className="size-4" />
      {label}
    </NavLink>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-svh bg-background text-foreground">
        <aside className="sticky top-0 flex h-svh w-56 shrink-0 flex-col gap-1 border-r p-3">
          <div className="mb-4 flex items-center gap-2 px-3 py-2">
            <ScaleIcon className="size-5 shrink-0" />
            <div className="leading-tight">
              <div className="font-semibold tracking-wide">J.U.L.I.A.</div>
              <div className="text-[10px] text-muted-foreground">
                Jurisprudencia Unificada, Leyes e Inteligencia Aplicada
              </div>
            </div>
          </div>
          <NavItem to="/clientes" icon={UsersIcon} label="Clientes" />
          <NewWorkDialog
            trigger={
              <button
                type="button"
                className="flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <FilePlusIcon className="size-4" />
                Nuevo caso
              </button>
            }
          />
          <NavItem to="/servicios" icon={BriefcaseIcon} label="Servicios" />
          <NavItem to="/reportes" icon={BarChart3Icon} label="Reportes" />
          <NavItem to="/leyes" icon={BookOpenIcon} label="Leyes" />
          <NavItem to="/reglas" icon={ListChecksIcon} label="Reglas del despacho" />
          <NavItem to="/ajustes" icon={SettingsIcon} label="Ajustes" />
          <div className="mt-auto pt-4">
            <ThemeToggle />
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <Routes>
            <Route path="/" element={<Navigate to="/clientes" replace />} />
            <Route path="/clientes" element={<ClientsPage />} />
            <Route path="/clientes/:id" element={<ClientDetailPage />} />
            <Route path="/casos/:id" element={<WorkPage />} />
            <Route path="/servicios" element={<ServicesPage />} />
            <Route path="/reportes" element={<ReportsPage />} />
            <Route path="/leyes" element={<LeyesPage />} />
            <Route path="/reglas" element={<ReglasPage />} />
            <Route path="/ajustes" element={<AjustesPage />} />
          </Routes>
        </main>
      </div>
      <Toaster richColors position="top-right" />
    </BrowserRouter>
  )
}
