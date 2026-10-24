#!/bin/bash
# Respaldo de J.U.L.I.A. (Mac). La logica vive en backend/app/respaldo.py,
# la misma que usa Windows; el destino es la carpeta de respaldos de Ajustes.
#
#   bash launcher/respaldo.sh            # respalda ahora
#   bash launcher/respaldo.sh --si-falta # solo si hoy no se ha respaldado
#                                        # (asi lo llama start.sh al abrir la app)

set -euo pipefail
BACKEND_DIR="$(cd "$(dirname "$0")/../backend" && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$BACKEND_DIR"
exec .venv/bin/python -m app.respaldo "$@"
