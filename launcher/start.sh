#!/bin/bash
# Paso 9: arranca todo lo que necesita J.U.L.I.A. y abre el navegador.
# Lo ejecuta "JULIA.app" (ver crear_app.sh); tambien se puede
# correr a mano: bash launcher/start.sh
#
# Si algo ya esta corriendo (Ollama, MySQL, el servidor), no lo vuelve a
# arrancar -- abrir la app dos veces solo abre otra pestana.

set -u

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/logs"
PORT="${ASISTENTE_PORT:-8000}"
URL="http://127.0.0.1:$PORT"

# Las apps de macOS arrancan con un PATH minimo; agregamos Homebrew y DBngin.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$LOG_DIR"

avisar() {
  # Muestra un mensaje en ventana (no en Terminal) y termina.
  /usr/bin/osascript -e "display dialog \"$1\" with title \"J.U.L.I.A.\" buttons {\"OK\"} default button 1 with icon caution" >/dev/null 2>&1
  exit 1
}

puerto_abierto() { /usr/bin/nc -z 127.0.0.1 "$1" >/dev/null 2>&1; }

esperar_puerto() {  # esperar_puerto <puerto> <segundos>
  for _ in $(seq 1 "$2"); do
    puerto_abierto "$1" && return 0
    sleep 1
  done
  return 1
}

# 1. MySQL (lo maneja DBngin)
if ! puerto_abierto 3306; then
  open -ga DBngin 2>/dev/null
  esperar_puerto 3306 20 || avisar "La base de datos (MySQL) no esta encendida.\n\nAbre DBngin, presiona Start en MySQL y vuelve a abrir J.U.L.I.A."
fi

# 1b. Respaldo del dia (si todavia no hay), en segundo plano para no hacer
#     esperar al abrir la app. Ver launcher/respaldo.sh.
nohup bash "$PROJECT_DIR/launcher/respaldo.sh" --si-falta >>"$LOG_DIR/respaldo.log" 2>&1 &

# 2. Ollama (el modelo de IA)
if ! puerto_abierto 11434; then
  if command -v brew >/dev/null 2>&1; then
    brew services start ollama >>"$LOG_DIR/launcher.log" 2>&1
  else
    nohup ollama serve >>"$LOG_DIR/ollama.log" 2>&1 &
  fi
  esperar_puerto 11434 20 || avisar "No se pudo encender Ollama (el modelo de IA). Avisale a Cesar."
fi

# 3. Frontend compilado (solo la primera vez, o si alguien borro dist/)
if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
  (cd "$FRONTEND_DIR" && npm run build) >>"$LOG_DIR/launcher.log" 2>&1 \
    || avisar "No se pudo preparar la pantalla de la app. Avisale a Cesar (ver logs/launcher.log)."
fi

# 4. Servidor (FastAPI) -- sirve la API y el frontend en el mismo puerto
if ! puerto_abierto "$PORT"; then
  cd "$BACKEND_DIR" || avisar "No encontre la carpeta backend."
  nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT" \
    >>"$LOG_DIR/servidor.log" 2>&1 &
  echo $! >"$LOG_DIR/servidor.pid"

  ok=0
  for _ in $(seq 1 40); do
    if curl -fs "$URL/api/health" >/dev/null 2>&1; then ok=1; break; fi
    sleep 0.5
  done
  [ "$ok" = 1 ] || avisar "El servidor no arranco. Avisale a Cesar (ver logs/servidor.log)."
fi

# 5. Abrir en el navegador de siempre
open "$URL"
