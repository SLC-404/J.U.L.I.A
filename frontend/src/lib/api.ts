// Cliente minimo para el backend FastAPI. En desarrollo Vite reenvia /api/*
// a http://127.0.0.1:8000 (ver vite.config.ts).

const BASE = '/api'

export type Client = {
  id: number
  name: string
  email: string | null
  phone: string | null
  address: string | null
  created_at: string
}

export type Service = {
  id: number
  name: string
  price: number
  status: string
}

export type Work = {
  id: number
  client_id: number
  service_id: number
  price: number
  status: string
  started_at: string | null
  notes: string | null
  created_at: string
}

export type WorkMessage = {
  id: number
  work_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
  updated_at?: string
  tipo?: 'escrito' | 'consulta'
}

export type Carpetas = {
  archivos: string
  respaldos: string
  por_defecto: { archivos: string; respaldos: string }
  avisos: string[]
}

export type WorkFile = {
  id: number
  work_id: number
  filename: string
  path: string
  type: string
  status: string
  created_at: string
}

export type ClientReportRow = {
  client_id: number
  name: string
  works_count: number
  total: number
}

export type CodigoLegal = {
  archivo: string
  nombre: string
  fuente: string
  ultima_reforma: string | null
  revisado: string | null
  actualizado: string | null
  error: string | null
  descargado: boolean
}

export type ProgramacionLeyes = {
  ultima_ejecucion: string | null
  origen: 'manual' | 'automatica' | null
  resultado: string | null
  proxima_ejecucion: string | null
}

export type TrabajoLeyes = {
  corriendo: boolean
  origen: 'manual' | 'automatica' | null
  mensaje: string
  inicio: string | null
  fin: string | null
  resultados: { codigo: string; estado: 'actualizado' | 'al_dia' | 'error'; detalle: string }[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    let detail = `Error ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // respuesta sin JSON; nos quedamos con el codigo
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

const put = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(body) })

export const api = {
  clients: {
    list: () => request<Client[]>('/clients/'),
    get: (id: number) => request<Client>(`/clients/${id}`),
    create: (data: Partial<Client>) => post<Client>('/clients/', data),
    update: (id: number, data: Partial<Client>) => put<Client>(`/clients/${id}`, data),
  },
  services: {
    list: () => request<Service[]>('/services/'),
    create: (data: Partial<Service>) => post<Service>('/services/', data),
    update: (id: number, data: Partial<Service>) => put<Service>(`/services/${id}`, data),
  },
  works: {
    list: (clientId?: number) =>
      request<Work[]>(clientId ? `/works/?client_id=${clientId}` : '/works/'),
    get: (id: number) => request<Work>(`/works/${id}`),
    create: (data: Partial<Work>) => post<Work>('/works/', data),
    update: (id: number, data: Partial<Work>) => put<Work>(`/works/${id}`, data),
  },
  messages: {
    list: (workId: number) => request<WorkMessage[]>(`/works/${workId}/messages/`),
    send: (workId: number, content: string) =>
      post<WorkMessage>(`/works/${workId}/messages/`, { content }),
    update: (workId: number, messageId: number, content: string) =>
      put<WorkMessage>(`/works/${workId}/messages/${messageId}`, { content }),
    cambios: (workId: number, messageId: number) =>
      request<{ resumen: string }>(`/works/${workId}/messages/${messageId}/cambios`),
    seccion: (workId: number, messageId: number, nombre: string) =>
      request<{ texto: string }>(
        `/works/${workId}/messages/${messageId}/seccion?nombre=${encodeURIComponent(nombre)}`,
      ),
  },
  files: {
    list: (workId: number) => request<WorkFile[]>(`/works/${workId}/files`),
    fromMessage: (workId: number, messageId: number, filename?: string) =>
      post<WorkFile>(
        `/works/${workId}/files/from-message/${messageId}`,
        filename ? { filename } : undefined,
      ),
    downloadUrl: (fileId: number) => `${BASE}/files/${fileId}/download`,
  },
  reports: {
    clients: () => request<ClientReportRow[]>('/reports/clients'),
  },
  ajustes: {
    reglas: () => request<{ reglas: string }>('/ajustes/reglas'),
    guardarReglas: (reglas: string) => put<{ reglas: string }>('/ajustes/reglas', { reglas }),
    carpetas: () => request<Carpetas>('/ajustes/carpetas'),
    guardarCarpetas: (c: { archivos?: string; respaldos?: string }) => put<Carpetas>('/ajustes/carpetas', c),
    abrirCarpeta: (cual: 'archivos' | 'respaldos') => post<{ ok: boolean }>('/ajustes/carpetas/abrir', { cual }),
  },
  leyes: {
    estado: () =>
      request<{ codigos: CodigoLegal[]; trabajo: TrabajoLeyes; programacion: ProgramacionLeyes }>(
        '/leyes/',
      ),
    actualizar: () => post<{ arrancado: boolean; trabajo: TrabajoLeyes }>('/leyes/actualizar'),
  },
}

export const money = (n: number) =>
  n.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })

export const shortDate = (iso: string) =>
  new Date(iso).toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' })
