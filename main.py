"""
Punto de Entrada Principal — Proyecto Fastrack
===============================================

Inicializa y ejecuta los servidores de la aplicación:
  - API FastAPI (puerto interno 8000) para validaciones
  - Servidor Flask (puerto principal) para el frontend

Uso para desarrollo:

    # Terminal 1 — API de validación
    py -3.12 -m uvicorn main:api --reload --port 8000

    # Terminal 2 — Frontend web
    py -3.12 main.py

Uso en producción (Render / Nube):

    py main.py
    (Lee la variable PORT del entorno, o usa 5000 por defecto)
"""

import os
import threading
import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as validacion_router
from app.servidor import crear_app_flask


# =============================================================================
# APLICACIÓN FASTAPI (API DE VALIDACIÓN)
# =============================================================================

api = FastAPI(
    title="Fastrack — API de Validación de Precios",
    description=(
        "API para validar archivos Excel de precios residenciales. "
        "Ejecuta 10 validaciones de calidad de datos."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware CORS
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@api.get("/verificar", tags=["Sistema"])
def verificar_servicio():
    """Endpoint de verificación de salud del servicio."""
    return {"mensaje": "API de validación funcionando correctamente"}

# Registrar router de validación
api.include_router(validacion_router)


# =============================================================================
# APLICACIÓN FLASK (FRONTEND)
# =============================================================================

flask_app = crear_app_flask()


# =============================================================================
# EJECUCIÓN — LOCAL Y PRODUCCIÓN
# =============================================================================

def iniciar_api_background(puerto_api: int):
    """Inicia la API FastAPI en un hilo separado."""
    uvicorn.run(api, host="127.0.0.1", port=puerto_api, log_level="warning")


def esperar_api(puerto_api: int, intentos: int = 10):
    """Espera a que la API esté lista antes de continuar."""
    import requests as req
    url = f"http://127.0.0.1:{puerto_api}/verificar"
    for i in range(intentos):
        try:
            r = req.get(url, timeout=2)
            if r.status_code == 200:
                print(f"  API lista (intento {i + 1})")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("  ADVERTENCIA: La API no respondió en tiempo esperado")
    return False


if __name__ == "__main__":
    puerto_flask = int(os.environ.get("PORT", 5000))
    puerto_api = int(os.environ.get("API_PORT", 8000))

    # Iniciar FastAPI en background
    hilo_api = threading.Thread(
        target=iniciar_api_background,
        args=(puerto_api,),
        daemon=True
    )
    hilo_api.start()

    # Esperar a que la API esté lista
    esperar_api(puerto_api)

    print("\n" + "=" * 56)
    print("  Fastrack -- Validador de Precios")
    print(f"  Frontend: http://0.0.0.0:{puerto_flask}")
    print(f"  API:      http://127.0.0.1:{puerto_api}")
    print("=" * 56 + "\n")

    flask_app.run(
        host="0.0.0.0",
        port=puerto_flask,
        debug=False
    )
