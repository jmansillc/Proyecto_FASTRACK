"""
Punto de Entrada Principal — Proyecto Fastrack
===============================================

Ejecuta el servidor Flask que sirve el frontend y las validaciones.

Uso para desarrollo:

    py -3.12 main.py

Uso en producción (Render / Nube):

    python main.py
    (Lee la variable PORT del entorno, o usa 5000 por defecto)
"""

import os
from app.servidor import crear_app_flask


# =============================================================================
# APLICACIÓN FLASK
# =============================================================================

flask_app = crear_app_flask()


# =============================================================================
# EJECUCIÓN
# =============================================================================

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))

    print("\n" + "=" * 56)
    print("  Fastrack -- Validador de Precios")
    print(f"  URL: http://0.0.0.0:{puerto}")
    print("=" * 56 + "\n")

    flask_app.run(
        host="0.0.0.0",
        port=puerto,
        debug=False
    )
