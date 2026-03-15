"""
Módulo de Base de Datos — Proyecto Fastrack
=============================================

Gestiona la conexión a SQLite y provee funciones CRUD para:
- usuarios: autenticación y roles
- cargas: flujo de archivos Excel (Negocio → TI → BD)
- bitacora_acciones: auditoría de acciones

Esquema diseñado para migración futura a PostgreSQL o MariaDB.

Uso:
    from app.nucleo.database import inicializar_bd, obtener_conexion
"""

import json
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app.nucleo.config import RUTA_BD, ADMIN_CORREO, ADMIN_NOMBRE, ADMIN_CONTRASENA


# =============================================================================
# DDL — DEFINICIÓN DE TABLAS
# =============================================================================

SQL_CREAR_TABLA_USUARIOS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    correo          TEXT    NOT NULL UNIQUE,
    contrasena_hash TEXT    NOT NULL,
    nombre          TEXT    NOT NULL,
    rol             TEXT    NOT NULL CHECK (rol IN ('admin', 'negocio', 'ti')),
    activo          INTEGER NOT NULL DEFAULT 1,
    fecha_creacion  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);
"""

SQL_CREAR_TABLA_CARGAS = """
CREATE TABLE IF NOT EXISTS cargas (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id            INTEGER NOT NULL,
    nombre_archivo        TEXT    NOT NULL,
    archivo_datos         BLOB,
    estado                TEXT    NOT NULL DEFAULT 'validando'
                                 CHECK (estado IN ('validando', 'aprobado', 'cargado_bd', 'rechazado')),
    resultado_validacion  TEXT,
    total_filas           INTEGER DEFAULT 0,
    total_errores         INTEGER DEFAULT 0,
    fecha_subida          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')),
    fecha_aprobacion      TEXT,
    fecha_carga_bd        TEXT,
    usuario_ti_id         INTEGER,
    notas                 TEXT,
    FOREIGN KEY (usuario_id)    REFERENCES usuarios(id),
    FOREIGN KEY (usuario_ti_id) REFERENCES usuarios(id)
);
"""

SQL_CREAR_TABLA_BITACORA = """
CREATE TABLE IF NOT EXISTS bitacora_acciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL,
    accion          TEXT    NOT NULL,
    detalle         TEXT,
    tabla_afectada  TEXT,
    registro_id     INTEGER,
    fecha           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
"""


# =============================================================================
# CONEXIÓN
# =============================================================================

def obtener_conexion(ruta_bd: str = None) -> sqlite3.Connection:
    """
    Abre y retorna una conexión a la base de datos SQLite.

    Parámetros:
        ruta_bd: Ruta al archivo .db. Si es None usa RUTA_BD de config.

    Retorna:
        sqlite3.Connection con row_factory = sqlite3.Row
    """
    if ruta_bd is None:
        ruta_bd = RUTA_BD

    conexion = sqlite3.connect(ruta_bd)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion


# =============================================================================
# INICIALIZACIÓN
# =============================================================================

def inicializar_bd(ruta_bd: str = None) -> None:
    """
    Crea todas las tablas si no existen y genera el usuario admin
    por defecto si la tabla de usuarios está vacía.

    Parámetros:
        ruta_bd: Ruta al archivo .db. Si es None usa RUTA_BD de config.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(SQL_CREAR_TABLA_USUARIOS)
        cursor.execute(SQL_CREAR_TABLA_CARGAS)
        cursor.execute(SQL_CREAR_TABLA_BITACORA)
        conexion.commit()

        # Crear admin por defecto si no existe ningún usuario
        cursor.execute("SELECT COUNT(*) FROM usuarios;")
        total = cursor.fetchone()[0]

        if total == 0:
            crear_usuario(
                correo=ADMIN_CORREO,
                contrasena=ADMIN_CONTRASENA,
                nombre=ADMIN_NOMBRE,
                rol="admin",
                conexion=conexion,
            )
            print(f"[BD] Usuario admin creado: {ADMIN_CORREO}")

        print("[BD] Base de datos inicializada correctamente.")
    finally:
        conexion.close()


def obtener_tablas(ruta_bd: str = None) -> list:
    """
    Retorna la lista de nombres de tablas en la base de datos.

    Parámetros:
        ruta_bd: Ruta al archivo .db.

    Retorna:
        list[str]: Nombres de las tablas existentes.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [fila[0] for fila in cursor.fetchall()]
    finally:
        conexion.close()


# =============================================================================
# CRUD — USUARIOS
# =============================================================================

def crear_usuario(
    correo: str,
    contrasena: str,
    nombre: str,
    rol: str,
    conexion: sqlite3.Connection = None,
    ruta_bd: str = None,
) -> int:
    """
    Crea un nuevo usuario en la base de datos.

    Parámetros:
        correo: Email único del usuario.
        contrasena: Contraseña en texto plano (se almacena hasheada).
        nombre: Nombre completo del usuario.
        rol: 'admin', 'negocio' o 'ti'.
        conexion: Conexión existente (opcional).
        ruta_bd: Ruta a la BD (si no se pasa conexión).

    Retorna:
        int: ID del usuario creado.

    Raises:
        sqlite3.IntegrityError: Si el correo ya existe.
        sqlite3.IntegrityError: Si el rol no es válido.
    """
    cerrar = False
    if conexion is None:
        conexion = obtener_conexion(ruta_bd)
        cerrar = True

    try:
        hash_contrasena = generate_password_hash(contrasena, method="pbkdf2:sha256")
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO usuarios (correo, contrasena_hash, nombre, rol) "
            "VALUES (?, ?, ?, ?);",
            (correo, hash_contrasena, nombre, rol),
        )
        conexion.commit()
        return cursor.lastrowid
    finally:
        if cerrar:
            conexion.close()


def obtener_usuario_por_correo(
    correo: str, ruta_bd: str = None
) -> dict | None:
    """
    Busca un usuario por su correo electrónico.

    Retorna:
        dict con los datos del usuario, o None si no existe.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE correo = ?;", (correo,))
        fila = cursor.fetchone()
        return dict(fila) if fila else None
    finally:
        conexion.close()


def obtener_usuario_por_id(
    usuario_id: int, ruta_bd: str = None
) -> dict | None:
    """
    Busca un usuario por su ID.

    Retorna:
        dict con los datos del usuario, o None si no existe.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = ?;", (usuario_id,))
        fila = cursor.fetchone()
        return dict(fila) if fila else None
    finally:
        conexion.close()


def listar_usuarios(ruta_bd: str = None) -> list[dict]:
    """
    Retorna todos los usuarios registrados.

    Retorna:
        list[dict]: Lista de diccionarios con datos de cada usuario.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, correo, nombre, rol, activo, fecha_creacion "
            "FROM usuarios ORDER BY id;"
        )
        return [dict(fila) for fila in cursor.fetchall()]
    finally:
        conexion.close()


def verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    """
    Compara una contraseña en texto plano contra su hash almacenado.

    Retorna:
        True si la contraseña coincide, False en caso contrario.
    """
    return check_password_hash(contrasena_hash, contrasena)


def cambiar_contrasena(
    usuario_id: int, nueva_contrasena: str, ruta_bd: str = None
) -> bool:
    """
    Actualiza la contraseña de un usuario.

    Retorna:
        True si se actualizó, False si el usuario no existe.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        nuevo_hash = generate_password_hash(nueva_contrasena, method="pbkdf2:sha256")
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET contrasena_hash = ? WHERE id = ?;",
            (nuevo_hash, usuario_id),
        )
        conexion.commit()
        return cursor.rowcount > 0
    finally:
        conexion.close()


def cambiar_estado_usuario(
    usuario_id: int, activo: bool, ruta_bd: str = None
) -> bool:
    """
    Activa o desactiva un usuario.

    Retorna:
        True si se actualizó, False si el usuario no existe.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET activo = ? WHERE id = ?;",
            (1 if activo else 0, usuario_id),
        )
        conexion.commit()
        return cursor.rowcount > 0
    finally:
        conexion.close()


def eliminar_usuario(usuario_id: int, ruta_bd: str = None) -> bool:
    """
    Elimina un usuario de la base de datos de forma permanente.
    Nota: Las acciones en la bitácora permanecerán pero sin relación F.K.
    (Si se desea integridad referencial estricta, usar borrado lógico o cascada).
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ?;", (usuario_id,))
        conexion.commit()
        return cursor.rowcount > 0
    finally:
        conexion.close()


# =============================================================================
# CRUD — CARGAS
# =============================================================================

def crear_carga(
    usuario_id: int,
    nombre_archivo: str,
    archivo_datos: bytes = None,
    resultado_validacion: dict = None,
    total_filas: int = 0,
    total_errores: int = 0,
    ruta_bd: str = None,
) -> int:
    """
    Registra una nueva carga de archivo Excel.

    Parámetros:
        usuario_id: ID del usuario que sube el archivo.
        nombre_archivo: Nombre original del archivo.
        archivo_datos: Bytes del archivo Excel (opcional).
        resultado_validacion: Dict con resultados de validación.
        total_filas: Número total de filas del archivo.
        total_errores: Número de errores encontrados.
        ruta_bd: Ruta a la BD.

    Retorna:
        int: ID de la carga creada.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        resultado_json = json.dumps(resultado_validacion) if resultado_validacion else None
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO cargas "
            "(usuario_id, nombre_archivo, archivo_datos, resultado_validacion, "
            "total_filas, total_errores) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            (usuario_id, nombre_archivo, archivo_datos, resultado_json,
             total_filas, total_errores),
        )
        conexion.commit()
        return cursor.lastrowid
    finally:
        conexion.close()


def obtener_carga_por_id(
    carga_id: int, ruta_bd: str = None
) -> dict | None:
    """
    Busca una carga por su ID.

    Retorna:
        dict con datos de la carga (resultado_validacion como dict), o None.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM cargas WHERE id = ?;", (carga_id,))
        fila = cursor.fetchone()
        if fila is None:
            return None
        datos = dict(fila)
        if datos.get("resultado_validacion"):
            datos["resultado_validacion"] = json.loads(datos["resultado_validacion"])
        return datos
    finally:
        conexion.close()


def listar_cargas_por_usuario(
    usuario_id: int, ruta_bd: str = None
) -> list[dict]:
    """
    Retorna todas las cargas de un usuario específico.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, nombre_archivo, estado, total_filas, total_errores, "
            "fecha_subida, fecha_aprobacion, fecha_carga_bd "
            "FROM cargas WHERE usuario_id = ? ORDER BY fecha_subida DESC;",
            (usuario_id,),
        )
        return [dict(fila) for fila in cursor.fetchall()]
    finally:
        conexion.close()


def listar_cargas_por_estado(
    estado: str, ruta_bd: str = None
) -> list[dict]:
    """
    Retorna todas las cargas con un estado específico.

    Parámetros:
        estado: 'validando', 'aprobado', 'cargado_bd' o 'rechazado'.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT c.id, c.nombre_archivo, c.estado, c.total_filas, "
            "c.total_errores, c.fecha_subida, c.fecha_aprobacion, "
            "u.nombre AS subido_por "
            "FROM cargas c "
            "JOIN usuarios u ON c.usuario_id = u.id "
            "WHERE c.estado = ? "
            "ORDER BY c.fecha_subida DESC;",
            (estado,),
        )
        return [dict(fila) for fila in cursor.fetchall()]
    finally:
        conexion.close()


def actualizar_estado_carga(
    carga_id: int,
    nuevo_estado: str,
    usuario_ti_id: int = None,
    notas: str = None,
    ruta_bd: str = None,
) -> bool:
    """
    Actualiza el estado de una carga y registra timestamps relevantes.

    Parámetros:
        carga_id: ID de la carga.
        nuevo_estado: 'aprobado', 'cargado_bd' o 'rechazado'.
        usuario_ti_id: ID del usuario TI (para cargado_bd).
        notas: Comentarios opcionales.

    Retorna:
        True si se actualizó, False si la carga no existe.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        ahora = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        cursor = conexion.cursor()

        if nuevo_estado == "aprobado":
            cursor.execute(
                "UPDATE cargas SET estado = ?, fecha_aprobacion = ?, notas = ? "
                "WHERE id = ?;",
                (nuevo_estado, ahora, notas, carga_id),
            )
        elif nuevo_estado == "cargado_bd":
            cursor.execute(
                "UPDATE cargas SET estado = ?, fecha_carga_bd = ?, "
                "usuario_ti_id = ?, notas = ? WHERE id = ?;",
                (nuevo_estado, ahora, usuario_ti_id, notas, carga_id),
            )
        else:
            cursor.execute(
                "UPDATE cargas SET estado = ?, notas = ? WHERE id = ?;",
                (nuevo_estado, notas, carga_id),
            )

        conexion.commit()
        return cursor.rowcount > 0
    finally:
        conexion.close()


# =============================================================================
# CRUD — BITÁCORA DE ACCIONES
# =============================================================================

def registrar_accion(
    usuario_id: int,
    accion: str,
    detalle: str = None,
    tabla_afectada: str = None,
    registro_id: int = None,
    ruta_bd: str = None,
) -> int:
    """
    Registra una acción en la bitácora de auditoría.

    Parámetros:
        usuario_id: ID del usuario que realizó la acción.
        accion: Descripción corta (ej: 'login', 'crear_usuario', 'aprobar_carga').
        detalle: Descripción larga opcional.
        tabla_afectada: Nombre de la tabla afectada.
        registro_id: ID del registro afectado.

    Retorna:
        int: ID de la entrada en la bitácora.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO bitacora_acciones "
            "(usuario_id, accion, detalle, tabla_afectada, registro_id) "
            "VALUES (?, ?, ?, ?, ?);",
            (usuario_id, accion, detalle, tabla_afectada, registro_id),
        )
        conexion.commit()
        return cursor.lastrowid
    finally:
        conexion.close()


def listar_bitacora(
    limite: int = 50, ruta_bd: str = None
) -> list[dict]:
    """
    Retorna las últimas entradas de la bitácora.

    Parámetros:
        limite: Número máximo de registros a retornar.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT b.id, b.accion, b.detalle, b.tabla_afectada, "
            "b.registro_id, b.fecha, u.nombre AS usuario_nombre, u.correo "
            "FROM bitacora_acciones b "
            "JOIN usuarios u ON b.usuario_id = u.id "
            "ORDER BY b.id DESC LIMIT ?;",
            (limite,),
        )
        return [dict(fila) for fila in cursor.fetchall()]
    finally:
        conexion.close()


def listar_bitacora_por_usuario(
    usuario_id: int, limite: int = 50, ruta_bd: str = None
) -> list[dict]:
    """
    Retorna las últimas acciones de un usuario específico.
    """
    conexion = obtener_conexion(ruta_bd)
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, accion, detalle, tabla_afectada, registro_id, fecha "
            "FROM bitacora_acciones "
            "WHERE usuario_id = ? "
            "ORDER BY id DESC LIMIT ?;",
            (usuario_id, limite),
        )
        return [dict(fila) for fila in cursor.fetchall()]
    finally:
        conexion.close()
