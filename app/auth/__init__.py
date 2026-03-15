"""
Módulo de Autenticación — Proyecto Fastrack
=============================================

Maneja login, sesiones y control de acceso por rol usando flask-login.

Uso:
    from app.auth import login_manager, UsuarioSesion, requiere_rol
"""

from functools import wraps

from flask import redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, current_user

from app.nucleo.database import (
    obtener_usuario_por_correo,
    obtener_usuario_por_id,
    verificar_contrasena,
    registrar_accion,
)


# =============================================================================
# LOGIN MANAGER
# =============================================================================

login_manager = LoginManager()
"""Instancia global de LoginManager para configurar en la app."""

login_manager.login_view = "login"
login_manager.login_message = "Debe iniciar sesion para acceder."
login_manager.login_message_category = "error"


# =============================================================================
# MODELO DE USUARIO PARA SESIÓN
# =============================================================================

class UsuarioSesion(UserMixin):
    """
    Representación del usuario en la sesión de Flask-Login.

    Atributos:
        id: ID del usuario en la BD.
        correo: Email del usuario.
        nombre: Nombre completo.
        rol: 'admin', 'negocio' o 'ti'.
        activo: Si el usuario está activo.
    """

    def __init__(self, id, correo, nombre, rol, activo):
        self.id = id
        self.correo = correo
        self.nombre = nombre
        self.rol = rol
        self.activo = activo

    @property
    def is_active(self):
        """Flask-Login usa esto para verificar si el usuario está activo."""
        return bool(self.activo)

    @staticmethod
    def desde_dict(datos: dict) -> "UsuarioSesion":
        """Crea una instancia desde un diccionario de la BD."""
        return UsuarioSesion(
            id=datos["id"],
            correo=datos["correo"],
            nombre=datos["nombre"],
            rol=datos["rol"],
            activo=datos["activo"],
        )


@login_manager.user_loader
def cargar_usuario(user_id: str):
    """Callback de flask-login para recargar usuario desde la BD."""
    datos = obtener_usuario_por_id(int(user_id))
    if datos is None:
        return None
    return UsuarioSesion.desde_dict(datos)


# =============================================================================
# FUNCIÓN DE LOGIN
# =============================================================================

def login_usuario(correo: str, contrasena: str) -> tuple:
    """
    Verifica credenciales y retorna el usuario si son válidas.

    Parámetros:
        correo: Email del usuario.
        contrasena: Contraseña en texto plano.

    Retorna:
        (UsuarioSesion, None) si login exitoso.
        (None, str) con mensaje de error si falla.
    """
    usuario = obtener_usuario_por_correo(correo)

    if usuario is None:
        return None, "Correo o contrasena incorrectos."

    if not verificar_contrasena(contrasena, usuario["contrasena_hash"]):
        return None, "Correo o contrasena incorrectos."

    if not usuario["activo"]:
        return None, "Su cuenta esta desactivada. Contacte al administrador."

    return UsuarioSesion.desde_dict(usuario), None


# =============================================================================
# DECORADOR DE ROL
# =============================================================================

def requiere_rol(*roles):
    """
    Decorador que restringe acceso a rutas según el rol del usuario.

    Uso:
        @app.route("/admin/usuarios")
        @requiere_rol("admin")
        def admin_usuarios():
            ...
    """
    def decorador(f):
        @wraps(f)
        def funcion_decorada(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.rol not in roles:
                return (
                    '{"error": "No tiene permisos para esta accion."}',
                    403,
                    {"Content-Type": "application/json"},
                )
            return f(*args, **kwargs)
        return funcion_decorada
    return decorador
