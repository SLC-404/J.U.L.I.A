# J.U.L.I.A. — Jurisprudencia Unificada, Leyes e Inteligencia Aplicada

Asistente legal del despacho de la Lic. Juana Landa Hernández (proyecto DEV002).

App local (no web publica) para administrar clientes/casos de un despacho de
derecho civil, con un agente de IA (local, Ollama) que ayuda a redactar
escritos usando RAG sobre los codigos legales del Edomex y los propios
formatos del despacho.

Ver `docs/ARQUITECTURA.md` para el detalle completo de decisiones.

## Progreso

- [x] Paso 1: carpeta del proyecto + FastAPI minimo ("hello world")
- [x] Paso 2: conexion a MySQL + modelos SQLModel (clients, services, works, work_files, work_messages)
- [x] Paso 3: endpoints CRUD de clients/services/works
- [x] Paso 4: Ollama + endpoint de chat (`/works/{id}/messages`) -- probado de punta a punta
- [x] Paso 5: RAG (Chroma + LlamaIndex) -- ingesta corrida (719 paginas, 1091 fragmentos en chroma_db/)
- [x] Paso 6: generar .docx desde el chat (`POST /works/{id}/files/from-message/{message_id}`)
- [x] Paso 7: frontend React (Vite + Tailwind + shadcn/ui en `frontend/`)
- [x] Paso 8: reportes (`GET /reports/clients` + pantalla Reportes: casos y total acordado por cliente)
- [x] Paso 9: lanzador sin Terminal (`launcher/JULIA.app`)

## Correr el backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajusta si tu MySQL usa otro usuario/password
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000/docs para ver y probar todos los endpoints
(Swagger, viene gratis con FastAPI). Toda la API vive bajo `/api` (ej.
`/api/clients/`); las rutas que se mencionan abajo sin `/api` son
relativas a ese prefijo.

## Correr el frontend (en otra Terminal, con uvicorn ya corriendo)

```bash
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173. En desarrollo, Vite reenvia `/api/*` al backend
en :8000 (ver `frontend/vite.config.ts`), asi que no hace falta CORS.

Pantallas: Clientes -> detalle del cliente con sus casos -> caso (chat con
el asistente + "Exportar a Word" en cada respuesta + panel de documentos
para descargar). Ademas, Servicios para el catalogo y precios de lista.

## Probar el chat (necesita Ollama corriendo con el modelo ya bajado)

```bash
ollama pull llama3.1:8b
```

Luego, desde /docs: crea un cliente, un servicio y un work, y mandale un
mensaje a `POST /works/{id}/messages` con `{"content": "..."}`.

## Paso 5: RAG con los codigos legales

El agente busca en las leyes antes de responder, usando Chroma (base de
datos vectorial local, un archivo mas en tu disco) + LlamaIndex. Para
activarlo:

### 1. Descarga los 3 PDFs oficiales

Pega esto en tu Terminal (NO en la VM de Claude, en tu Terminal normal, para
que tenga internet sin restricciones):

```bash
cd ~/Documents/www/DEV002/backend/legal_corpus
curl -L -o codigo_civil_edomex.pdf "https://docs.mexico.justia.com/estatales/mexico/codigo-civil-del-estado-de-mexico.pdf"
curl -L -o codigo_procedimientos_civiles_edomex.pdf "https://docs.mexico.justia.com/estatales/mexico/codigo-de-procedimientos-civiles-del-estado-de-mexico.pdf"
curl -L -o codigo_nacional_procedimientos_civiles_familiares.pdf "https://www.diputados.gob.mx/LeyesBiblio/pdf/CNPCF.pdf"
ls -la
```

Cargamos los dos codigos de procedimientos (el del Edomex y el nacional)
porque el Estado de Mexico esta en transicion entre ambos -- asi el agente
puede citar de cual sale cada cosa y avisar si hay que confirmar cual aplica.

### 2. Instala las librerias nuevas y el modelo de embeddings

```bash
cd ~/Documents/www/DEV002/backend
source .venv/bin/activate
pip install -r requirements.txt
ollama pull nomic-embed-text
```

### 3. Corre la ingesta (una sola vez; tarda varios minutos)

```bash
python scripts/ingest_legal_corpus.py
```

Esto lee los 3 PDFs, los parte en pedazos y los guarda indexados en
`backend/chroma_db/` (se crea solo, no lo subas a git -- ya esta en
.gitignore).

### 4. Reinicia uvicorn y prueba

Para a uvicorn (Ctrl+C) y vuelve a correrlo. Manda un mensaje con una
pregunta legal real (ej. `"que articulo habla de la compraventa en el
codigo civil?"`) a `POST /works/{id}/messages` y la respuesta deberia citar
el codigo correspondiente.

## Paso 6: exportar escritos a Word (.docx)

Cuando una respuesta del agente ya es el escrito que quieres, exportala:

1. `GET /works/{id}/messages` -- busca el `id` del mensaje del agente.
2. `POST /works/{id}/files/from-message/{message_id}` -- body opcional
   `{"filename": "Contrato compraventa"}` (sin extension). Genera el .docx
   (Arial 12, interlineado 1.5, justificado) y lo registra en `work_files`
   con `type = "borrador_ia"`.
3. `GET /works/{id}/files` -- lista los documentos del caso.
4. `GET /files/{file_id}/download` -- descarga el .docx.

Los archivos quedan en
`backend/storage/clientes/{client_id}_{cliente}/{work_id}_{servicio}/`
(ya esta en .gitignore).

## Paso 9: como lo abre mi ama (sin Terminal)

`launcher/JULIA.app` es un icono (una balanza) que con doble clic:

1. Enciende MySQL (abre DBngin) si esta apagado.
2. Enciende Ollama si esta apagado.
3. Compila el frontend si `frontend/dist/` no existe.
4. Arranca el servidor (uvicorn, sin `--reload`) en http://127.0.0.1:8000,
   que sirve la API y el frontend juntos.
5. Abre esa direccion en el navegador.

Si algo ya esta corriendo no lo repite, asi que abrir la app dos veces
solo abre otra pestana. Si algo falla, sale una ventana con el aviso (no
la Terminal), y los detalles quedan en `logs/`.

### Instalarlo en la Mac de mi ama (una sola vez)

```bash
cd ~/Documents/www/DEV002
(cd frontend && npm install && npm run build)
bash launcher/crear_app.sh
```

La primera vez que se abre, macOS pregunta si "JULIA" puede
acceder a la carpeta Documentos: hay que darle **Permitir** (si no, la app
se queda esperando sin abrir nada). Solo pasa una vez.

Luego arrastra `launcher/JULIA.app` al Dock. La app tiene la ruta
del proyecto fija adentro: si mueves la carpeta DEV002, vuelve a correr
`crear_app.sh`.

Recomendado: en DBngin, activa "Start on login" para MySQL, y deja Ollama
como servicio de Homebrew (`brew services start ollama`) para que ya esten
encendidos al prender la Mac.

### Despues de cambiar el frontend

El lanzador usa `frontend/dist/`, no el modo dev. Despues de cambiar algo
en `frontend/src/`, recompila con `npm run build` y reinicia el servidor:

```bash
bash launcher/stop.sh
```

(y vuelve a abrir la app).

## Escritos del despacho (el asistente aprende el estilo de la Lic. Juana)

Los escritos de la USB (carpeta `MAMA`) se copiaron ordenados por cliente a
`backend/escritos_despacho/` (no se sube a git: tiene datos reales):

- `clientes/<Nombre>/` -- un folder por cliente (el cliente se tomo de lo que
  dice ADENTRO del escrito, no del nombre del archivo).
- `_asuntos_propios_lic_juana/`, `juicios_mercantiles/`, `_formatos_generales/`
- `_trabajo_municipio_dif/`, `_escuela_michael/`, `_personal/`,
  `_sin_texto_revisar/` -- no se usan en el asistente.
- `manifiesto.csv` -- de donde salio cada archivo, a que cliente se asigno y
  si se usa en el asistente (columna `usar_en_asistente`). Se abre en
  Excel/Numbers: si algo quedo mal, se corrige ahi.

Para que el asistente los use (y despues de cambiar el CSV o agregar escritos):

```bash
cd backend
source .venv/bin/activate
python scripts/ingest_escritos.py
```

Al pedir un escrito en el chat, el asistente detecta el tipo (demanda,
contestacion, alegatos, copias certificadas, contrato...), busca el escrito
del despacho mas parecido de ese tipo, le quita los nombres de las partes y
lo usa como modelo de formato y estilo. El Word exportado respeta el formato
del despacho (rubro a la derecha, H E C H O S centrado, firma con cedula).

Modelo: `qwen3.5:9b` (en `.env`). Con escritos de ejemplo, `llama3.1:8b` se
negaba a redactar. Tarda ~1 minuto por escrito largo. **Todo lo que redacta
es borrador**: puede citar articulos o causales que no aplican y agregar
hechos que no estan en las notas; la abogada revisa siempre.

### Clientes, servicios y casos importados de los escritos

```bash
cd backend
source .venv/bin/activate
python scripts/registrar_clientes_y_servicios.py   # 89 clientes + 28 servicios
python scripts/importar_casos.py --seco            # muestra que casos crearia
python scripts/importar_casos.py                   # crea casos y adjunta escritos
```

Un caso por numero de expediente (los escritos sin numero se juntan con el
caso del mismo servicio). En las notas quedan expediente, juicio, juzgado y
partes. Los escritos quedan adjuntos al caso (tipo "subido"). Precios en $0 y
estado "terminado" solo si algun escrito dice que la sentencia causo
ejecutoria: hay que confirmarlos con la Lic. Ambos scripts se pueden volver a
correr sin duplicar.

## Respaldos

Cada vez que se abre **JULIA.app**, si ese dia todavia no hay
respaldo, se hace uno solo (en segundo plano) en `~/Respaldos-JULIA/`:

- `base_datos/dev002_AAAA-MM-DD_HHMM.sql.gz`: clientes, servicios, casos y
  chats. Se guardan los ultimos 60.
- `archivos/storage/` y `archivos/escritos_despacho/`: espejo de todos los
  documentos. Nunca se borra nada ahi, aunque se borre en la app.

Va **fuera de Documentos** a proposito: si la Mac sincroniza Documentos con
iCloud, los datos de clientes no deben salir de la computadora. Para tener
una copia fuera de la Mac (por si se descompone), copiar esa carpeta a una USB
cada semana o cada mes.

Respaldar a mano en cualquier momento:

```bash
bash launcher/respaldo.sh
```

### Restaurar (si se perdio o se dano la base)

```bash
gunzip -c ~/Respaldos-JULIA/base_datos/dev002_FECHA.sql.gz | /Users/Shared/DBngin/mysql/9.7.1_arm/bin/mysql -uroot -h127.0.0.1 dev002
rsync -a ~/Respaldos-JULIA/archivos/storage/ backend/storage/
rsync -a ~/Respaldos-JULIA/archivos/escritos_despacho/ backend/escritos_despacho/
```

(Probado: el respaldo cargado en una base nueva trae exactamente los mismos
clientes, casos, archivos y mensajes.) La base vectorial (`chroma_db/`) no se
respalda: se reconstruye con `python scripts/ingest_legal_corpus.py` y
`python scripts/ingest_escritos.py`.

## Leyes al dia (boton "Buscar actualizaciones")

En la pantalla **Leyes** de la app se ve que version de cada codigo usa el
asistente (fecha de su ultima reforma) y hay un boton **Buscar
actualizaciones** que:

1. Baja cada codigo de su fuente oficial: Codigo Civil y Codigo de
   Procedimientos Civiles del Edomex desde legislacion.edomex.gob.mx, y el
   Codigo Nacional de Procedimientos Civiles y Familiares desde
   diputados.gob.mx.
2. Confirma por el titulo que sea el codigo correcto (si el Edomex cambia la
   numeracion de sus archivos, lo busca entre los demas).
3. Si cambio, reemplaza el PDF y vuelve a indexar SOLO ese codigo. Si no,
   termina en segundos con "Todo esta al dia".
4. Si el sitio no responde, reintenta una vez y si no, avisa y se queda con
   la version anterior (no se pierde nada).

Ademas se hace **sola cada mes**: el servidor trae un programador que cada
hora revisa `backend/legal_corpus/programacion.json` (ultima ejecucion y
proxima = ultima + 1 mes). Si ya toco, lanza la revision. Corre mientras la
app este abierta; si la Mac estaba apagada el dia que tocaba, se hace en
cuanto se abra. Si falla por falta de internet, se reintenta al dia
siguiente. El boton manual tambien cuenta como ejecucion (mueve la proxima a
un mes despues). Para probarlo rapido: `LEYES_ESPERA_INICIAL_SEG=2
LEYES_REVISAR_CADA_SEG=5` y poner `proxima_ejecucion` en el pasado.

Lo que se sabe de cada version queda en
`backend/legal_corpus/versiones.json`, y el asistente cita cada articulo con
la fecha de reforma del codigo del que sale. La lista de codigos y fuentes
esta en `backend/app/leyes.py` (para agregar otro codigo, se agrega ahi).

## Fundamento legal, modo corregir y reglas del despacho (oct 2026)

Mejoras tras revisar el chat real del caso de María Pérez:

- **Leyes por articulo** (`app/articulos.py`): cada codigo se separa en
  articulos con su numero, epigrafe y Libro/Titulo/Capitulo. Se indexa un
  fragmento por articulo y se guarda una "biblioteca" en
  `legal_corpus/articulos/`. Antes eran pedazos de pagina y la busqueda
  traia articulos generales (1.1-1.8) en vez de los del tema.
- **Fundamento por servicio** (`app/fundamentos.py`): para cada servicio se
  sabe de que capitulos sale el fundamento sustantivo (Codigo Civil) y el
  procesal (Codigo de Procedimientos), mas articulos "ancla" (ej. 4.42-4.45
  en sucesorios). El asistente escribe el DERECHO como el despacho: "Fundan
  la presente... / Norman el procedimiento...". Si la materia no esta
  cargada (mercantil, penal, amparo), deja [fundamento: ...] en vez de
  inventar.
- **Modo corregir** (`app/routers/messages.py`): si ya hay un escrito y la
  abogada pide cambios ("quita", "agrega", "coloca"...), se corrige ESE
  escrito y no se vuelve a redactar desde cero.
- **Reglas del despacho** (pantalla en la app, tabla `ajustes`):
  preferencias que el asistente sigue siempre. Precargadas con lo que la
  Lic. corrigio en el chat de María.
- **Revision automatica** (`app/revision.py`): corrige el nombre del cliente
  si el modelo lo deforma, y le da la fecha de hoy y de los proximos dias.
- **Word**: reconoce "P R O T E S T O" con letras separadas; la firma de la
  abogada sale a la izquierda con su cedula.

## Asistente de voz (oct 2026)

Todo local: la voz de la Lic. y los datos de los clientes no salen de la
computadora. Funciona igual en Mac y en Windows 11 (Chrome o Edge).

- **Cómo se usa:** al crear un caso se elige "Escrito" o "Asistente de voz"
  (también se cambia con el botón de arriba del caso; se recuerda por caso).
  En modo voz el micrófono **escucha siempre** y lo que dice la Lic. se va
  escribiendo en "Correcciones dictadas" (lo puede corregir con el teclado).
  **Nada se manda a J.U.L.I.A. hasta que da clic en "Enviar actualización".**
  Cuando termina, J.U.L.I.A. **lee en voz alta qué cambió** ("Hice 2 cambios.
  En los hechos ahora dice: …") y se repite hasta que el escrito quede bien.
  Mientras J.U.L.I.A. habla, el micrófono se pausa para no escucharse a sí misma.
- En cada escrito hay botones "Escuchar cambios" y "Leer todo"; en las
  respuestas a preguntas, "Escuchar".
- Al enviar, J.U.L.I.A. avisa en voz alta ("Va, estoy trabajando en los
  cambios…"). Lo que la Lic. dicte mientras espera NO se pierde: queda para
  la siguiente actualización.
- **Comandos de voz** (frase completa, sola; se ejecutan en lugar de
  escribirse — ver `frontend/src/lib/comandos.ts`). Siempre sobre el último
  escrito:

  | Dice la Lic. | Qué hace |
  |---|---|
  | "Léeme los hechos" / el derecho / las prestaciones / las pruebas / el proemio / los puntos petitorios / la firma | Lee solo esa parte |
  | "Léeme todo" | Lee el escrito completo |
  | "¿Qué cambiaste?" | Lee el resumen de cambios |
  | "Repite" | Repite lo último que dijo J.U.L.I.A. |
  | "Envía la actualización" | Igual que el botón |
  | "Borra lo dictado" | Limpia las correcciones dictadas |
  | "Ya quedó, pásalo a Word" | Exporta a Word (y aprende si ella lo editó) |
  | "¿Qué puedo decir?" | Lee esta lista |

  Una corrección como "en los hechos léeme la fecha" o "borra el hecho
  tres" NO es comando: se escribe como corrección.
- **Oído:** Whisper "small" (faster-whisper, CPU). Se le pasan los nombres
  del cliente, del servicio y de las notas del caso para que los escriba bien.
- **Voz:** **Chatterbox multilingüe** (la más humana; elegida oct 2026),
  con acento mexicano copiado de `backend/modelos_voz/voz_julia.wav`. Si ese
  archivo no existe se arma solo con Piper. Para cambiar la voz, reemplázalo
  por una grabación limpia de ~10 segundos (WAV) de quien quieras y reinicia.
  **Piper** (`es_MX-claude-high`) queda de respaldo: si Chatterbox no está
  instalado o falla, habla Piper. Para usar solo Piper (más rápido):
  `VOZ_MOTOR=piper` en `backend/.env`.
- **Velocidad de Chatterbox** (Mac M5): un aviso corto ~7 s y un resumen
  de cambios ~13 s con la GPU de la Mac; ~2x más en CPU. En la laptop de
  Windows (sin tarjeta de video) será más lento. Por eso el navegador lo
  pide **frase por frase**: empieza a hablar con la primera (~10 s) mientras
  genera las siguientes. Al entrar al modo voz se precargan los modelos.
- **Memoria:** Chatterbox ocupa ~3 GB de RAM, más Whisper (~0.5 GB) y el
  modelo de Ollama (~7 GB). Con 16 GB alcanza; conviene cerrar otras apps.
- **Modelos:** viven en `backend/modelos_voz/` (no van a git). Si faltan, se
  bajan solos la primera vez (necesita internet esa única vez): Whisper
  ~460 MB, Piper ~60 MB y Chatterbox ~3 GB. La primera frase tarda unos segundos más porque
  carga el modelo.
- **Librerías:** `pip install -r backend/requirements.txt` (faster-whisper,
  piper-tts, chatterbox-tts, num2words, numpy, certifi). Chatterbox pide
  `setuptools<81`; ya está en requirements.
- **Permiso del micrófono:** la primera vez el navegador pregunta; hay que
  dar "Permitir". En Mac, además, Ajustes del Sistema → Privacidad →
  Micrófono → activar el navegador. En Windows 11: Configuración →
  Privacidad → Micrófono. Funciona en `http://127.0.0.1` (el navegador lo
  trata como sitio seguro).
- Rutas: `POST /api/voz/transcribir`, `POST /api/voz/hablar`,
  `GET /api/works/{id}/messages/{mid}/cambios`,
  `GET /api/works/{id}/messages/{mid}/seccion?nombre=los hechos`, `GET /api/voz/estado`.

## Ajustes: dónde se guardan los archivos (oct 2026)

Pantalla **Ajustes** (menú de la izquierda). Ver `backend/app/carpetas.py`.

- **Carpeta de archivos** (por defecto `~/J.U.L.I.A.`, en Windows
  `C:\Users\<ella>\J.U.L.I.A.`): los Word de cada caso en
  `Casos\<Cliente>\<Servicio> (caso N)\<Servicio> AAAA-MM-DD HHMM.docx`.
- **Carpeta de respaldos** (por defecto `~/Respaldos-JULIA`): respaldo
  diario de la base y espejo de los documentos. Ahora lo hace
  `backend/app/respaldo.py` (igual en Mac y Windows); `launcher/respaldo.sh`
  solo lo llama.
- No van en Documentos a propósito (OneDrive/iCloud subirían datos de
  clientes a la nube); si se elige una carpeta en la nube, la app avisa.
- Los archivos de antes siguen en `backend/storage/` y se descargan igual.

## Repo público

En GitHub solo va el código (ver `.gitignore`): nada de `storage/`,
`escritos_despacho/`, `chroma_db/`, `.env`, `logs/` ni los scripts de la
importación inicial (`importar_casos.py`, `registrar_clientes_y_servicios.py`),
que traen la lista real de clientes y se quedan solo en la Mac.
`frontend/dist/` sí se sube, para que Windows no necesite Node.

## Windows (laptop de la Lic.)

Scripts en `launcher/windows/`. Todo queda en la computadora; internet solo
para instalar y para actualizarse.

### 1. En la Mac: armar el paquete de datos

```bash
cd backend && .venv/bin/python -m app.paquete exportar
```

Deja `~/JULIA-paquete-AAAA-MM-DD_HHMM.zip` (~140 MB) con la base, los Word
de los casos, los escritos del despacho, el índice del RAG y la voz de
J.U.L.I.A. **Trae datos de clientes: pásalo por USB y bórralo al terminar.**

### 2. En Windows: instalar (una vez)

PowerShell **como administrador** (clic derecho → Ejecutar como administrador):

```powershell
irm https://raw.githubusercontent.com/SLC-404/J.U.L.I.A/main/launcher/windows/instalar.ps1 | iex
```

- Instala con winget lo que falte: Git, uv (que trae su propio Python
  3.14), Ollama, MySQL y Visual C++.
- Baja el proyecto a `%LOCALAPPDATA%\JULIA\app`.
- MySQL queda como servicio `JULIA-MySQL` (arranca con Windows, solo escucha
  en 127.0.0.1, datos en `C:\ProgramData\JULIA\mysql`).
- Baja los modelos (~12 GB): qwen + nomic-embed-text, Whisper, Piper y
  Chatterbox.
- Pregunta por el paquete de datos: se arrastra el .zip a la ventana. Sin
  paquete, empieza vacía e indexa las leyes.
- Crea el ícono **J.U.L.I.A.** en el escritorio y en el menú Inicio.
- Se puede volver a correr para reparar: lo que ya está se salta.
- Log: `%LOCALAPPDATA%\JULIA\logs\instalacion.log`.

### 3. Uso diario

Doble clic en el ícono (`iniciar.ps1`): enciende MySQL y Ollama si hacen
falta, **se actualiza solo desde GitHub** (y reinstala librerías si
cambiaron), hace el respaldo del día y abre el navegador. Para detener:
`launcher\windows\detener.ps1`.

### Notas

- `backend/overrides.txt` quita dos dependencias de Chatterbox que no se
  usan (`spacy-pkuseg`, solo chino, y `gradio`, su demo): en Windows con
  Python 3.14 `spacy-pkuseg` pediría un compilador de C.
- Los `.doc` viejos se leen con el Word de la Lic. (`pywin32`); en la Mac
  con `textutil`.
- Importar un paquete encima de datos existentes: `python -m app.paquete
  importar paquete.zip --reemplazar` (lo de antes se aparta con fecha, no se
  borra).
- Sin probar todavía en Windows real: la primera instalación en la Huawei es
  la prueba de verdad (ver `logs\instalacion.log` si algo falla).
