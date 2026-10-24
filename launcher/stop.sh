#!/bin/bash
# Apaga el servidor de J.U.L.I.A. que arranco start.sh.
# (Ollama y MySQL se quedan encendidos; no estorban y los usa la app.)

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$PROJECT_DIR/logs/servidor.pid"

if [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Servidor detenido."
else
  echo "El servidor no estaba corriendo (o se arranco a mano, no con start.sh)."
fi
rm -f "$PID_FILE"
