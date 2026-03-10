"""
Servidor Flask — Proyecto Fastrack
===================================

Servidor Flask que sirve el frontend y ejecuta las validaciones
directamente (sin necesidad de un servidor FastAPI separado).

Uso:
    Importado desde main.py — no ejecutar directamente.
"""

import os
import io
import pandas as pd
from flask import Flask, request, render_template, jsonify, Response

from app.nucleo.config import (
    NOMBRE_HOJA,
    TAMANO_MAXIMO_MB,
    COLUMNAS_CLAVE,
    COLUMNAS_OBLIGATORIAS,
    COLUMNAS_VALOR_UNICO,
    COLUMNAS_PRECIO,
    COLUMNAS_FECHA,
    COLUMNAS_TEXTO,
    COLUMNAS_REQUERIDAS,
    PRECIO_MINIMO,
    PRECIO_MAXIMO,
    FORMATO_FECHA,
    VALORES_FIJOS,
    VALORES_PERMITIDOS,
    LONGITUDES_MAXIMAS,
)
from app.servicios.validaciones import (
    validar_estructura_excel,
    validar_nulos,
    validar_duplicados,
    validar_unicos,
    validar_precio,
    validar_fecha,
    validar_coherencia_fechas,
    validar_espacios_en_blanco,
    validar_longitud,
    validar_valores_permitidos,
)
from app.servicios.correcciones import autocorregir_valores_fijos


# =============================================================================
# CACHE EN MEMORIA
# =============================================================================

_cache_df_corregido = {}
"""Almacena temporalmente el DataFrame corregido para descarga."""


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

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
    """Verifica que el nombre del archivo tenga una extensión permitida."""
    _, extension = os.path.splitext(nombre_archivo)
    return extension.lower() in EXTENSIONES_PERMITIDAS


def ejecutar_validaciones(contenido_bytes: bytes, nombre_archivo: str) -> dict:
    """
    Ejecuta todas las validaciones sobre el contenido del archivo Excel.

    Parámetros:
        contenido_bytes: Bytes del archivo Excel.
        nombre_archivo: Nombre original del archivo.

    Retorna:
        dict: Resultado completo de todas las validaciones.
    """
    tamano_mb = len(contenido_bytes) / (1024 * 1024)
    if tamano_mb > TAMANO_MAXIMO_MB:
        return {
            "error": f"Archivo excede {TAMANO_MAXIMO_MB} MB ({tamano_mb:.1f} MB)"
        }

    buffer = io.BytesIO(contenido_bytes)

    # --- Validación de estructura (recibe bytes crudos) ---
    resultado_estructura = validar_estructura_excel(
        contenido_bytes, NOMBRE_HOJA, COLUMNAS_REQUERIDAS
    )

    if not resultado_estructura.get("es_valido"):
        return {
            "estructura": resultado_estructura,
            "resumen": {
                "total_validaciones": 1,
                "validaciones_exitosas": 0,
                "validaciones_fallidas": 1,
                "es_valido_global": False,
                "mensaje": "1 de 1 validaciones fallaron.",
            }
        }

    # --- Leer DataFrame ---
    buffer.seek(0)
    df = pd.read_excel(
        buffer,
        sheet_name=NOMBRE_HOJA,
        engine="openpyxl"
    )

    # --- Auto-corrección de valores fijos ---
    df_corregido, reporte_correcciones = autocorregir_valores_fijos(
        df, VALORES_FIJOS
    )

    # Guardar en cache para descarga posterior
    _cache_df_corregido["ultimo"] = df_corregido
    _cache_df_corregido["nombre_hoja"] = NOMBRE_HOJA

    # --- Ejecutar todas las validaciones ---
    resultado_nulos = validar_nulos(df, COLUMNAS_OBLIGATORIAS)
    resultado_duplicados = validar_duplicados(df, COLUMNAS_CLAVE)
    resultado_unicos = validar_unicos(df, COLUMNAS_VALOR_UNICO)
    resultado_precios = validar_precio(
        df, COLUMNAS_PRECIO, PRECIO_MINIMO, PRECIO_MAXIMO
    )
    resultado_fechas = validar_fecha(df, COLUMNAS_FECHA, FORMATO_FECHA)
    resultado_coherencia = validar_coherencia_fechas(
        df, "FECHA_EFECTIVA", "FECHA_FIN", FORMATO_FECHA
    )
    resultado_espacios = validar_espacios_en_blanco(df, COLUMNAS_TEXTO)
    resultado_longitud = validar_longitud(df, LONGITUDES_MAXIMAS)
    resultado_permitidos = validar_valores_permitidos(df, VALORES_PERMITIDOS)

    # --- Construir lista de resultados ---
    lista_resultados = [
        resultado_estructura,
        resultado_nulos,
        resultado_duplicados,
        resultado_unicos,
        resultado_precios,
        resultado_fechas,
        resultado_coherencia,
        resultado_espacios,
        resultado_longitud,
        resultado_permitidos,
    ]

    # --- Calcular resumen ---
    total_validaciones = len(lista_resultados)
    validaciones_exitosas = sum(
        1 for r in lista_resultados if r.get("es_valido")
    )

    return {
        "estructura": resultado_estructura,
        "nulos": resultado_nulos,
        "duplicados": resultado_duplicados,
        "unicos": resultado_unicos,
        "precios": resultado_precios,
        "fechas": resultado_fechas,
        "coherencia_fechas": resultado_coherencia,
        "espacios_en_blanco": resultado_espacios,
        "longitud": resultado_longitud,
        "valores_permitidos": resultado_permitidos,
        "correcciones_automaticas": reporte_correcciones,
        "resumen": {
            "total_validaciones": total_validaciones,
            "validaciones_exitosas": validaciones_exitosas,
            "validaciones_fallidas": total_validaciones - validaciones_exitosas,
            "es_valido_global": validaciones_exitosas == total_validaciones,
            "mensaje": (
                "Todas las validaciones pasaron correctamente."
                if validaciones_exitosas == total_validaciones
                else (
                    f"{total_validaciones - validaciones_exitosas} "
                    f"de {total_validaciones} validaciones fallaron."
                )
            )
        }
    }


# =============================================================================
# REGISTRO DE RUTAS
# =============================================================================

def registrar_rutas(app: Flask):
    """Registra todas las rutas de la aplicación Flask."""

    @app.route("/")
    def pagina_principal():
        """Sirve la página principal con el formulario de carga."""
        return render_template("index.html")

    @app.route("/validar", methods=["POST"])
    def validar_archivo():
        """
        Recibe un archivo desde el frontend, valida la extensión,
        y ejecuta todas las validaciones directamente.
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
            resultado = ejecutar_validaciones(contenido, archivo.filename)

            if "error" in resultado:
                return jsonify(resultado), 400

            return jsonify(resultado), 200

        except Exception as excepcion:
            return jsonify({
                "error": f"Error interno del servidor: {str(excepcion)}"
            }), 500

    @app.route("/descargar-corregido")
    def descargar_corregido():
        """Descarga el archivo Excel con las auto-correcciones aplicadas."""
        try:
            if "ultimo" not in _cache_df_corregido:
                return jsonify({
                    "error": "No hay archivo corregido disponible. Valide un archivo primero."
                }), 404

            df = _cache_df_corregido["ultimo"]
            hoja = _cache_df_corregido.get("nombre_hoja", "Datos")

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=hoja, index=False)
            buffer.seek(0)

            return Response(
                buffer.getvalue(),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment; filename=archivo_corregido.xlsx"
                }
            )

        except Exception as excepcion:
            return jsonify({
                "error": f"Error interno: {str(excepcion)}"
            }), 500

    @app.route("/aplicar-correcciones", methods=["POST"])
    def aplicar_correcciones():
        """Recibe el archivo con correcciones manuales y retorna el Excel limpio."""
        if "archivo" not in request.files:
            return jsonify({
                "error": "No se envió ningún archivo."
            }), 400

        archivo = request.files["archivo"]

        try:
            contenido = archivo.read()
            buffer = io.BytesIO(contenido)
            df = pd.read_excel(buffer, sheet_name=NOMBRE_HOJA, engine="openpyxl")

            # Aplicar auto-correcciones
            df_corregido, _ = autocorregir_valores_fijos(df, VALORES_FIJOS)

            buffer_salida = io.BytesIO()
            with pd.ExcelWriter(buffer_salida, engine="openpyxl") as writer:
                df_corregido.to_excel(writer, sheet_name=NOMBRE_HOJA, index=False)
            buffer_salida.seek(0)

            return Response(
                buffer_salida.getvalue(),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment; filename=archivo_final_limpio.xlsx"
                }
            )

        except Exception as excepcion:
            return jsonify({
                "error": f"Error interno: {str(excepcion)}"
            }), 500
