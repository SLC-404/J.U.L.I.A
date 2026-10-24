from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import leyes
from app.database import init_db
from app.routers import ajustes, clients, files, messages, reports, services, works
from app.routers import leyes as leyes_router
from app.routers import voz as voz_router

app = FastAPI(title="J.U.L.I.A. - Jurisprudencia Unificada, Leyes e Inteligencia Aplicada")

# Toda la API vive bajo /api. Asi, en el uso diario (Paso 9) el mismo
# servidor sirve la API y el frontend ya compilado, sin choques de rutas.
for module in (clients, services, works, messages, files, reports, leyes_router, ajustes, voz_router):
    app.include_router(module.router, prefix="/api")


@app.on_event("startup")
def on_startup():
    # Crea las tablas en MySQL si todavia no existen.
    init_db()
    # Revision mensual automatica de las leyes (ver app/leyes.py).
    leyes.iniciar_programador()


@app.get("/api/health")
def health_check():
    """Endpoint de prueba: si esto responde, FastAPI ya esta corriendo."""
    return {"status": "ok", "project": "DEV002"}


# --- Frontend compilado (frontend/dist, se genera con `npm run build`) ---
# En desarrollo no hace falta: Vite (npm run dev) sirve el frontend en :5173.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        # Archivos sueltos de public/ (favicon, etc.); todo lo demas es una
        # ruta de React (ej. /clientes/3) y se responde con index.html.
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
