"""
Servidor Flask (BFF) — Proyecto Fastrack
========================================

Servidor Flask que actúa como intermediario entre el frontend HTML
y la API FastAPI de validación. Sirve la página web y reenvía los
archivos a la API para su procesamiento.

Uso:
    Importado desde main.py — no ejecutar directamente.
"""

import os
from flask import Flask, request, render_template, jsonify, Response
import requests


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

URL_API_BASE = os.environ.get(
    "URL_API_VALIDACION",
    "http://127.0.0.1:8000/validar"
)
"""URL base de la API FastAPI de validación."""

URL_API_VALIDACION = f"{URL_API_BASE}/archivo"
URL_API_DESCARGAR = f"{URL_API_BASE}/descargar-corregido"
URL_API_APLICAR = f"{URL_API_BASE}/aplicar-correcciones"

EXTENSIONES_PERMITIDAS = {".xlsx"}
"""Extensiones de archivo aceptadas."""


def crear_app_flask() -> Flask:
    """
    Crea y configura la instancia de la aplicación Flask.

    Retorna:
        Flask: Instancia configurada de la aplicación.
    """
    directorio_templates = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates"
    )
    directorio_estaticos = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "static"
    )

    app = Flask(
        __name__,
        template_folder=directorio_templates,
        static_folder=directorio_estaticos,
    )

    registrar_rutas(app)
    return app


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def es_extension_valida(nombre_archivo: str) -> bool:
    """
    Verifica que el nombre del archivo tenga una extensión permitida.
    """
    _, extension = os.path.splitext(nombre_archivo)
    return extension.lower() in EXTENSIONES_PERMITIDAS


# =============================================================================
# REGISTRO DE RUTAS
# =============================================================================

def registrar_rutas(app: Flask):
    """
    Registra todas las rutas de la aplicación Flask.
    """

    @app.route("/")
    def pagina_principal():
        """Sirve la página principal con el formulario de carga."""
        return render_template("index.html")

    @app.route("/validar", methods=["POST"])
    def validar_archivo():
        """
        Recibe un archivo desde el frontend, valida la extensión,
        y lo reenvía a la API FastAPI para su procesamiento.
        """
        if "archivo" not in request.files:
            return jsonify({
                "error": "No se envió ningún archivo en la petición."
            }), 400

        archivo = request.files["archivo"]

        if archivo.filename == "":
            return jsonify({
                "error": "El nombre del archivo está vacío."
            }), 400

        if not es_extension_valida(archivo.filename):
            return jsonify({
                "error": (
                    f"Extensión no permitida. "
                    f"Solo se aceptan: {', '.join(EXTENSIONES_PERMITIDAS)}"
                )
            }), 400

        try:
            contenido = archivo.read()
            datos_archivo = {
                "archivo": (
                    archivo.filename,
                    contenido,
                    archivo.mimetype
                )
            }

            respuesta_api = requests.post(
                URL_API_VALIDACION,
                files=datos_archivo,
                timeout=300
            )

            if respuesta_api.status_code != 200:
                return jsonify({
                    "error": (
                        f"La API respondió con error: "
                        f"{respuesta_api.status_code} — {respuesta_api.text}"
                    )
                }), 502

            return jsonify(respuesta_api.json()), 200

        except requests.ConnectionError:
            return jsonify({
                "error": (
                    "No se pudo conectar con la API de validación. "
                    f"Verifique que esté corriendo en {URL_API_BASE}"
                )
            }), 502

        except requests.Timeout:
            return jsonify({
                "error": "La API de validación tardó demasiado en responder."
            }), 504

        except Exception as excepcion:
            return jsonify({
                "error": f"Error interno del servidor: {str(excepcion)}"
            }), 500

    @app.route("/descargar-corregido")
    def descargar_corregido():
        """
        Descarga el archivo Excel con las auto-correcciones aplicadas.
        """
        try:
            respuesta_api = requests.get(URL_API_DESCARGAR, timeout=300)

            if respuesta_api.status_code != 200:
                return jsonify({
                    "error": f"Error al descargar: {respuesta_api.text}"
                }), respuesta_api.status_code

            return Response(
                respuesta_api.content,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment; filename=archivo_corregido.xlsx"
                }
            )

        except requests.ConnectionError:
            return jsonify({
                "error": "No se pudo conectar con la API de validación."
            }), 502

        except Exception as excepcion:
            return jsonify({
                "error": f"Error interno: {str(excepcion)}"
            }), 500

    @app.route("/aplicar-correcciones", methods=["POST"])
    def aplicar_correcciones():
        """
        Recibe el archivo con correcciones manuales y retorna el Excel limpio.
        """
        if "archivo" not in request.files:
            return jsonify({
                "error": "No se envió ningún archivo."
            }), 400

        archivo = request.files["archivo"]

        try:
            contenido = archivo.read()
            datos_archivo = {
                "archivo": (
                    archivo.filename,
                    contenido,
                    archivo.mimetype
                )
            }

            respuesta_api = requests.post(
                URL_API_APLICAR,
                files=datos_archivo,
                timeout=300
            )

            if respuesta_api.status_code != 200:
                return jsonify({
                    "error": f"Error: {respuesta_api.text}"
                }), respuesta_api.status_code

            return Response(
                respuesta_api.content,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment; filename=archivo_final_limpio.xlsx"
                }
            )

        except requests.ConnectionError:
            return jsonify({
                "error": "No se pudo conectar con la API."
            }), 502

        except Exception as excepcion:
            return jsonify({
                "error": f"Error interno: {str(excepcion)}"
            }), 500
