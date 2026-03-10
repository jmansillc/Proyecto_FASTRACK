"""
Punto de Entrada Principal — Proyecto Fastrack
===============================================

Inicializa y ejecuta los servidores de la aplicación:
  - API FastAPI (puerto 8000) para validaciones
  - Servidor Flask (puerto 5000) para el frontend

Uso para desarrollo:

    # Terminal 1 — API de validación
    py -3.12 -m uvicorn main:api --reload

    # Terminal 2 — Frontend web
    py -3.12 main.py

Uso para producción:

    # API
    py -3.12 -m uvicorn main:api --host 0.0.0.0 --port 8000

    # Frontend
    py -3.12 -m gunicorn main:flask_app -b 0.0.0.0:5000
"""

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
        "Ejecuta 9 validaciones de calidad de datos."
    ),
    version="2.0.0",
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
# EJECUCIÓN DEL FRONTEND
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 56)
    print("  Fastrack -- Servidor Frontend")
    print("  URL: http://127.0.0.1:5000")
    print("  API debe estar corriendo en http://127.0.0.1:8000")
    print("=" * 56 + "\n")
    flask_app.run(debug=True, port=5000)
