"""
Servidor Flask — Proyecto Fastrack
===================================

Servidor Flask que sirve el frontend, ejecuta las validaciones y gestiona
la autenticacion y flujo de archivos por roles (Admin, Negocio, TI).
"""

import os
import io
import json
import pandas as pd
from flask import Flask, request, render_template, jsonify, Response, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import login_manager, login_usuario, requiere_rol
from app.nucleo.database import (
    inicializar_bd,
    crear_carga,
    obtener_carga_por_id,
    listar_cargas_por_usuario,
    listar_cargas_por_estado,
    actualizar_estado_carga,
    listar_usuarios,
    crear_usuario,
    cambiar_estado_usuario,
    eliminar_usuario,
    cambiar_contrasena,
    registrar_accion,
)
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
# CACHE EN MEMORIA (Para descarga inmediata tras validacion)
# =============================================================================

_cache_df_corregido = {}


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

EXTENSIONES_PERMITIDAS = {".xlsx"}


def crear_app_flask() -> Flask:
    """Crea y configura la instancia de la aplicacion Flask."""
    directorio_templates = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    directorio_estaticos = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

    app = Flask(
        __name__,
        template_folder=directorio_templates,
        static_folder=directorio_estaticos,
    )

    # Configuracion necesaria para sesiones
    app.secret_key = os.environ.get("SECRET_KEY", "fastrack-dev-key-123456")

    # Inicializar componentes
    login_manager.init_app(app)
    inicializar_bd()

    registrar_rutas(app)
    return app


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def es_extension_valida(nombre_archivo: str) -> bool:
    """Verifica que el nombre del archivo tenga una extension permitida."""
    _, extension = os.path.splitext(nombre_archivo)
    return extension.lower() in EXTENSIONES_PERMITIDAS


def ejecutar_validaciones(contenido_bytes: bytes, nombre_archivo: str) -> dict:
    """Ejecuta todas las validaciones sobre el contenido del archivo Excel."""
    tamano_mb = len(contenido_bytes) / (1024 * 1024)
    if tamano_mb > TAMANO_MAXIMO_MB:
        return {"error": f"Archivo excede {TAMANO_MAXIMO_MB} MB ({tamano_mb:.1f} MB)"}

    buffer = io.BytesIO(contenido_bytes)

    # --- Validacion de estructura ---
    resultado_estructura = validar_estructura_excel(contenido_bytes, NOMBRE_HOJA, COLUMNAS_REQUERIDAS)

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
    df = pd.read_excel(buffer, sheet_name=NOMBRE_HOJA, engine="openpyxl")

    # --- Auto-correccion de valores fijos ---
    df_corregido, reporte_correcciones = autocorregir_valores_fijos(df, VALORES_FIJOS)

    # Guardar en cache para descarga posterior antes de cargar a BD
    # Usamos un ID de sesion o el ID de usuario si esta logueado
    if current_user.is_authenticated:
        cache_key = str(current_user.id)
        _cache_df_corregido[cache_key] = {
            "df": df_corregido,
            "nombre_hoja": NOMBRE_HOJA
        }
    else:
        # Fallback para pruebas o anonimos si aplica
        _cache_df_corregido["ultimo"] = {
            "df": df_corregido,
            "nombre_hoja": NOMBRE_HOJA
        }

    # --- Ejecutar todas las validaciones ---
    resultado_nulos = validar_nulos(df, COLUMNAS_OBLIGATORIAS)
    resultado_duplicados = validar_duplicados(df, COLUMNAS_CLAVE)
    resultado_unicos = validar_unicos(df, COLUMNAS_VALOR_UNICO)
    resultado_precios = validar_precio(df, COLUMNAS_PRECIO, PRECIO_MINIMO, PRECIO_MAXIMO)
    resultado_fechas = validar_fecha(df, COLUMNAS_FECHA, FORMATO_FECHA)
    resultado_coherencia = validar_coherencia_fechas(df, "FECHA_EFECTIVA", "FECHA_FIN", FORMATO_FECHA)
    resultado_espacios = validar_espacios_en_blanco(df, COLUMNAS_TEXTO)
    resultado_longitud = validar_longitud(df, LONGITUDES_MAXIMAS)
    resultado_permitidos = validar_valores_permitidos(df, VALORES_PERMITIDOS)

    lista_resultados = [
        resultado_estructura, resultado_nulos, resultado_duplicados, resultado_unicos,
        resultado_precios, resultado_fechas, resultado_coherencia, resultado_espacios,
        resultado_longitud, resultado_permitidos,
    ]

    total_validaciones = len(lista_resultados)
    validaciones_exitosas = sum(1 for r in lista_resultados if r.get("es_valido"))

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
            "total_registros": len(df),
            "total_validaciones": total_validaciones,
            "validaciones_exitosas": validaciones_exitosas,
            "validaciones_fallidas": total_validaciones - validaciones_exitosas,
            "es_valido_global": validaciones_exitosas == total_validaciones,
            "mensaje": (
                "Archivo validado correctamente al 100%."
                if validaciones_exitosas == total_validaciones
                else f"{total_validaciones - validaciones_exitosas} errores encontrados."
            )
        }
    }


# =============================================================================
# REGISTRO DE RUTAS
# =============================================================================

def registrar_rutas(app: Flask):
    """Registra todas las rutas de la aplicacion Flask."""

    # --- AUTENTICACIÓN ---

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("home"))

        correo_previo = ""
        error = None

        if request.method == "POST":
            correo = request.form.get("correo")
            contrasena = request.form.get("contrasena")
            correo_previo = correo

            usuario, msg_error = login_usuario(correo, contrasena)

            if usuario:
                login_user(usuario)
                registrar_accion(usuario.id, "login", f"Acceso exitoso: {correo}")
                return redirect(url_for("home"))
            else:
                error = msg_error

        return render_template("login.html", error=error, correo_previo=correo_previo)

    @app.route("/logout")
    @login_required
    def logout():
        registrar_accion(current_user.id, "logout")
        logout_user()
        return redirect(url_for("login"))

    # --- RUTA PRINCIPAL (SELECTOR DE PANEL) ---

    @app.route("/")
    @login_required
    def home():
        if current_user.rol == "admin":
            return render_template("panel_admin.html", usuario=current_user)
        elif current_user.rol == "ti":
            return render_template("panel_ti.html", usuario=current_user)
        else:
            # rol negocio
            return render_template("index.html", usuario=current_user)

    # --- FUNCIONES DE NEGOCIO (Validador) ---

    @app.route("/validar", methods=["POST"])
    @login_required
    @requiere_rol("negocio", "admin")
    def validar_archivo():
        if "archivo" not in request.files:
            return jsonify({"error": "No se envio ningun archivo."}), 400

        archivo = request.files["archivo"]
        if not es_extension_valida(archivo.filename):
            return jsonify({"error": "Extension no permitida (solo .xlsx)"}), 400

        try:
            contenido = archivo.read()
            resultado = ejecutar_validaciones(contenido, archivo.filename)
            if "error" in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado), 200
        except Exception as e:
            return jsonify({"error": f"Error interno: {str(e)}"}), 500

    @app.route("/descargar-corregido")
    @login_required
    def descargar_corregido():
        """Descarga el Excel en memoria con auto-correcciones fijos."""
        cache_key = str(current_user.id)
        if cache_key not in _cache_df_corregido:
            return jsonify({"error": "No hay correcciones en cache. Por favor valide un archivo primero."}), 404

        item = _cache_df_corregido[cache_key]
        df = item["df"]
        hoja = item["nombre_hoja"]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=hoja, index=False)
        buffer.seek(0)

        return Response(
            buffer.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=archivo_corregido.xlsx"}
        )

    # --- FLUJO DE CARGA (Negocio -> TI) ---

    @app.route("/cargas/subir", methods=["POST"])
    @login_required
    @requiere_rol("negocio", "admin")
    def subir_carga_aprobada():
        """Recibe el OK de Negocio y guarda el Excel validado en BD."""
        datos = request.json
        if not datos or "nombre_archivo" not in datos:
            return jsonify({"error": "Datos incompletos"}), 400

        # Obtener el excel corregido del cache
        cache_key = str(current_user.id)
        if cache_key not in _cache_df_corregido:
            return jsonify({"error": "El excel ya no esta en cache. Por favor valide de nuevo."}), 400

        item = _cache_df_corregido[cache_key]
        df = item["df"]
        hoja = item["nombre_hoja"]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=hoja, index=False)
        excel_bytes = buffer.getvalue()

        try:
            carga_id = crear_carga(
                usuario_id=current_user.id,
                nombre_archivo=datos["nombre_archivo"],
                archivo_datos=excel_bytes,
                resultado_validacion=datos["resultado_validacion"],
                total_filas=datos["total_filas"],
                total_errores=datos["total_errores"]
            )
            
            # Cambiar a estado aprobado para que TI lo vea
            from app.nucleo.database import actualizar_estado_carga
            actualizar_estado_carga(carga_id, "aprobado")
            
            registrar_accion(current_user.id, "subir_carga", f"ID: {carga_id}", "cargas", carga_id)
            return jsonify({"id": carga_id, "mensaje": "Enviado a TI"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/cargas/mis-cargas")
    @login_required
    def mis_cargas():
        return jsonify(listar_cargas_por_usuario(current_user.id))

    # --- FUNCIONES DE TI ---

    @app.route("/cargas/pendientes")
    @login_required
    @requiere_rol("ti", "admin")
    def cargas_pendientes():
        return jsonify(listar_cargas_por_estado("aprobado"))

    @app.route("/cargas/procesados")
    @login_required
    @requiere_rol("ti", "admin")
    def cargas_procesadas():
        return jsonify(listar_cargas_por_estado("cargado_bd"))

    @app.route("/cargas/descargar/<int:id>")
    @login_required
    @requiere_rol("ti", "admin")
    def descargar_carga(id):
        carga = obtener_carga_por_id(id)
        if not carga or not carga["archivo_datos"]:
            return "No encontrado", 404

        return Response(
            carga["archivo_datos"],
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={carga['nombre_archivo']}"}
        )

    @app.route("/cargas/procesar/<int:id>", methods=["POST"])
    @login_required
    @requiere_rol("ti", "admin")
    def procesar_carga(id):
        exito = actualizar_estado_carga(id, "cargado_bd", usuario_ti_id=current_user.id)
        if exito:
            registrar_accion(current_user.id, "procesar_carga", f"Carga {id} procesada", "cargas", id)
            return jsonify({"mensaje": "Procesado"}), 200
        return jsonify({"error": "No se pudo actualizar"}), 400

    # --- FUNCIONES DE ADMIN ---

    @app.route("/admin/usuarios", methods=["GET"])
    @login_required
    @requiere_rol("admin")
    def api_listar_usuarios():
        return jsonify(listar_usuarios())

    @app.route("/admin/usuarios", methods=["POST"])
    @login_required
    @requiere_rol("admin")
    def api_crear_usuario():
        datos = request.json
        try:
            uid = crear_usuario(
                correo=datos["correo"],
                contrasena=datos["contrasena"],
                nombre=datos["nombre"],
                rol=datos["rol"]
            )
            registrar_accion(current_user.id, "crear_usuario", f"Creado: {datos['correo']}", "usuarios", uid)
            return jsonify({"id": uid}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/admin/usuarios/<int:id>/estado", methods=["PUT"])
    @login_required
    @requiere_rol("admin")
    def api_estado_usuario(id):
        activo = request.json.get("activo", True)
        exito = cambiar_estado_usuario(id, activo)
        if exito:
            accion = "activar_usuario" if activo else "desactivar_usuario"
            registrar_accion(current_user.id, accion, f"Usuario ID: {id}", "usuarios", id)
            return jsonify({"mensaje": "OK"}), 200
        return jsonify({"error": "No encontrado"}), 404

    @app.route("/admin/usuarios/<int:id>", methods=["DELETE"])
    @login_required
    @requiere_rol("admin")
    def api_eliminar_usuario(id):
        # Evitar que el admin se elimine a si mismo
        if id == current_user.id:
            return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400
            
        exito = eliminar_usuario(id)
        if exito:
            registrar_accion(current_user.id, "eliminar_usuario", f"Usuario ID: {id} eliminado", "usuarios", id)
            return jsonify({"mensaje": "Usuario eliminado correctamente"}), 200
        return jsonify({"error": "No encontrado"}), 404

    @app.route("/admin/usuarios/<int:id>/reset-password", methods=["PUT"])
    @login_required
    @requiere_rol("admin")
    def api_reset_password(id):
        nueva_pass = "Fastrack123*"
        exito = cambiar_contrasena(id, nueva_pass)
        if exito:
            registrar_accion(current_user.id, "reset_password_admin", f"Reset a usuario ID: {id}", "usuarios", id)
            return jsonify({"mensaje": f"Contrasena reseteada a: {nueva_pass}"}), 200
        return jsonify({"error": "No encontrado"}), 404

    @app.route("/perfil/cambiar-contrasena", methods=["POST"])
    @login_required
    def api_cambiar_propia_contrasena():
        datos = request.json
        pass_actual = datos.get("actual")
        pass_nueva = datos.get("nueva")

        if not pass_actual or not pass_nueva:
            return jsonify({"error": "Datos incompletos"}), 400

        # Verificar contraseña actual
        from app.nucleo.database import obtener_usuario_por_id, verificar_contrasena
        u_db = obtener_usuario_por_id(current_user.id)
        if not verificar_contrasena(pass_actual, u_db["contrasena_hash"]):
            return jsonify({"error": "Contrasena actual incorrecta"}), 401

        if len(pass_nueva) < 6:
            return jsonify({"error": "La nueva contrasena debe tener al menos 6 caracteres"}), 400

        exito = cambiar_contrasena(current_user.id, pass_nueva)
        if exito:
            registrar_accion(current_user.id, "cambio_password_propio", "Usuario cambio su propia contrasena", "usuarios", current_user.id)
            return jsonify({"mensaje": "Contrasena actualizada correctamente"}), 200
        return jsonify({"error": "Error al actualizar"}), 500
