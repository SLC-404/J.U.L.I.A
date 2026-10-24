# J.U.L.I.A. (DEV002) - Arquitectura y decisiones

J.U.L.I.A. = Jurisprudencia Unificada, Leyes e Inteligencia Aplicada.

## Que es

App local para el despacho de la mama de Cesar (derecho civil, Estado de
Mexico): administra clientes y casos, y un agente de IA la ayuda a redactar
escritos legales a partir de una base de conocimiento propia (RAG).

## Por que local y no web publica / app empacada

- Confidencialidad: datos de clientes de un despacho legal no deben salir
  de la computadora.
- Sin costo recurrente: nada de servidores ni suscripciones.
- Se descarto empacar como app de escritorio (Electron/Tauri) para evitar
  la complejidad de un instalador. En cambio: un servidor local (FastAPI)
  que se abre en el navegador de siempre.

## Stack

| Parte                | Decision          | Por que |
|-----------------------|-------------------|---------|
| Backend                | FastAPI (Python)  | Async nativo (util para streaming del chat), Pydantic de raiz, ideal para pura API + agente de IA |
| ORM                     | SQLModel          | Combina SQLAlchemy + Pydantic, hecho por el mismo autor de FastAPI |
| Base relacional         | MySQL             | Lo que ya domina Cesar |
| Base vectorial (RAG)    | ChromaDB          | Local, sin servidor aparte, integracion directa con LlamaIndex |
| Orquestacion RAG        | LlamaIndex        | Trae lectores de PDF/Word y el flujo de busqueda+generacion ya resueltos |
| Modelo de IA            | Ollama (local)    | Gratis, corre en la Mac del usuario (16 GB RAM): Llama 3.1 8B o Qwen 2.5 7B |
| Embeddings               | nomic-embed-text (Ollama) | Mismo Ollama, sin dependencia extra |
| Frontend                | React + Tailwind + shadcn/ui | Consistente con lo que ya usa Cesar en otros proyectos |
| Exportar escritos        | python-docx       | Los escritos legales en Mexico se siguen editando/imprimiendo en Word |
| Autenticacion            | Ninguna (por ahora) | Una sola usuaria, uso local |

## Modelo de datos (MySQL)

```
clients        id, name, email, phone, address
services       id, name, price, status            -- catalogo de servicios
works          id, client_id, service_id, price, status, started_at, notes
work_files     id, work_id, filename, path, type, status
work_messages  id, work_id, role, content
```

Todas con `created_at` / `updated_at`.

Puntos importantes:

- `works` es el caso/expediente REAL de un cliente (no solo una tabla
  pivote) -- aqui vive el precio realmente acordado, que puede diferir
  del precio de lista en `services`.
- `work_files.work_id` apunta siempre al caso especifico, nunca al
  catalogo de servicios -- si no, los documentos de distintos clientes
  con el mismo tipo de servicio se mezclarian.

## Diseno del agente de IA

Flujo hibrido: la usuaria elige/crea un cliente -> elige/crea un `work`
(caso) -> dentro de ese caso hay un chat con el agente.

- El chat vive en `work_messages`, **uno por caso**, no global ni por
  cliente -- se queda enfocado y no crece sin limite.
- Para que el agente pueda "aprender" de escritos anteriores de OTROS
  clientes (ej. "hazme algo como el contrato del otro cliente") sin
  necesitar un chat compartido pesado: cada `work_file` generado se
  indexa tambien en una coleccion de Chroma ("precedentes") con metadata
  `client_id` / `service_id` / `work_id`, filtrable por tipo de servicio.
- Cuando el agente redacta un documento completo (no solo platica), se
  guarda automatico como fila en `work_files` (`type = "borrador_ia"`) y
  se puede exportar a `.docx`.

## Base de conocimiento legal (RAG)

Alcance: derecho civil, Estado de Mexico.

- Codigo Civil del Estado de Mexico (sustantivo).
- Codigo de Procedimientos Civiles del Estado de Mexico (el "de toda la
  vida").
- Codigo Nacional de Procedimientos Civiles y Familiares (el nuevo,
  todavia en transicion de implementacion estado por estado) -- se carga
  TAMBIEN porque no esta resuelto cual aplica en cada caso; cada uno
  queda etiquetado por separado en la metadata para que el agente pueda
  decir de cual codigo esta citando.
- Mas adelante: los escritos propios que ya tiene la mama de Cesar (los
  mejores ejemplos de su propio estilo).

## Storage de archivos en disco

```
storage/clientes/{client_id}_{nombre-cliente}/{work_id}_{nombre-servicio}/archivo.docx
```

El id va antes del nombre para que nunca choque entre clientes con
nombre parecido, pero sigue siendo legible si alguien entra directo
por Finder.

## Reportes

Solo lo esencial: por cliente, cuantos casos (`works`) ha tenido y
cuanto se le ha cobrado en total. Nada de graficas ni filtros de fecha
por ahora.

## Como se abre en el dia a dia

`launcher/JULIA.app` (AppleScript generado con `osacompile`)
corre `launcher/start.sh`: enciende MySQL/Ollama si hace falta, arranca
uvicorn y abre el navegador. En ese modo FastAPI sirve tambien
`frontend/dist/` (el build de Vite), y la API vive bajo `/api` para no
chocar con las rutas de React.

## Pendiente de decidir

- Registro de pagos por caso (hoy el reporte suma el precio acordado).
- Ingesta real de los escritos propios de la mama de Cesar al RAG.
