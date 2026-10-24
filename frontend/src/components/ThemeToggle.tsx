import { useEffect, useState } from 'react'
import { MonitorIcon, MoonIcon, SunIcon } from 'lucide-react'
import { useTheme } from 'next-themes'

import { cn } from '@/lib/utils'

// Claro / Oscuro / Automatico (sigue al de la Mac). next-themes lo guarda en
// el navegador, asi que se queda como lo dejaron la ultima vez.
const OPCIONES = [
  { value: 'light', label: 'Claro', icon: SunIcon },
  { value: 'dark', label: 'Oscuro', icon: MoonIcon },
  { value: 'system', label: 'Automático', icon: MonitorIcon },
] as const

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  // Hasta montar no se sabe el tema guardado; evita marcar el boton equivocado.
  const [montado, setMontado] = useState(false)
  useEffect(() => setMontado(true), [])

  return (
    <div className="grid gap-1.5 px-3">
      <span className="text-xs text-muted-foreground">Apariencia</span>
      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {OPCIONES.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            title={label}
            aria-label={label}
            aria-pressed={montado && theme === value}
            onClick={() => setTheme(value)}
            className={cn(
              'flex flex-1 items-center justify-center rounded-md py-1.5 text-muted-foreground transition-colors hover:text-foreground',
              montado && theme === value && 'bg-background text-foreground shadow-sm',
            )}
          >
            <Icon className="size-4" />
          </button>
        ))}
      </div>
    </div>
  )
}
