"""
Tests Unitarios para Base de Datos — Proyecto Fastrack
========================================================

Cada test usa una BD SQLite en memoria para no afectar la BD real.

Ejecutar con:
    py -3.12 -m pytest tests/test_database.py -v
"""

import sys
import os
import json
import pytest

# Agregar raíz del proyecto al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nucleo.database import (
    obtener_conexion,
    inicializar_bd,
    obtener_tablas,
    crear_usuario,
    obtener_usuario_por_correo,
    obtener_usuario_por_id,
    listar_usuarios,
    verificar_contrasena,
    cambiar_contrasena,
    cambiar_estado_usuario,
    crear_carga,
    obtener_carga_por_id,
    listar_cargas_por_usuario,
    listar_cargas_por_estado,
    actualizar_estado_carga,
    registrar_accion,
    listar_bitacora,
    listar_bitacora_por_usuario,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db_tmp(tmp_path):
    """Crea una BD temporal para cada test."""
    ruta = str(tmp_path / "test_fastrack.db")
    inicializar_bd(ruta)
    return ruta


# =============================================================================
# TESTS — INICIALIZACIÓN
# =============================================================================

class TestInicializacion:
    def test_inicializar_bd_crea_tablas(self, db_tmp):
        """Verifica que se creen las 3 tablas correctamente."""
        tablas = obtener_tablas(db_tmp)
        assert "usuarios" in tablas
        assert "cargas" in tablas
        assert "bitacora_acciones" in tablas
        assert len(tablas) == 3

    def test_usuario_admin_por_defecto(self, db_tmp):
        """Verifica que el admin se cree automáticamente."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        assert admin is not None
        assert admin["rol"] == "admin"
        assert admin["nombre"] == "Administrador"
        assert admin["activo"] == 1

    def test_inicializar_dos_veces_no_duplica_admin(self, db_tmp):
        """Reinicializar no debe crear un segundo admin."""
        inicializar_bd(db_tmp)
        usuarios = listar_usuarios(db_tmp)
        admins = [u for u in usuarios if u["correo"] == "admin@fastrack.com"]
        assert len(admins) == 1


# =============================================================================
# TESTS — CRUD USUARIOS
# =============================================================================

class TestCrudUsuarios:
    def test_crear_usuario(self, db_tmp):
        """Crear un usuario y verificar que se puede leer."""
        uid = crear_usuario(
            correo="juan@test.com",
            contrasena="Pass123!",
            nombre="Juan Pérez",
            rol="negocio",
            ruta_bd=db_tmp,
        )
        assert uid > 0

        usuario = obtener_usuario_por_id(uid, db_tmp)
        assert usuario["correo"] == "juan@test.com"
        assert usuario["nombre"] == "Juan Pérez"
        assert usuario["rol"] == "negocio"
        assert usuario["activo"] == 1

    def test_correo_unico(self, db_tmp):
        """Crear dos usuarios con el mismo correo debe fallar."""
        crear_usuario("dup@test.com", "Pass1!", "Dup", "negocio", ruta_bd=db_tmp)
        with pytest.raises(Exception):
            crear_usuario("dup@test.com", "Pass2!", "Dup2", "ti", ruta_bd=db_tmp)

    def test_rol_invalido(self, db_tmp):
        """Crear usuario con rol no válido debe fallar."""
        with pytest.raises(Exception):
            crear_usuario("bad@test.com", "Pass!", "Bad", "superadmin", ruta_bd=db_tmp)

    def test_listar_usuarios(self, db_tmp):
        """Listar usuarios incluye el admin y los creados."""
        crear_usuario("u1@test.com", "P1!", "U1", "negocio", ruta_bd=db_tmp)
        crear_usuario("u2@test.com", "P2!", "U2", "ti", ruta_bd=db_tmp)
        usuarios = listar_usuarios(db_tmp)
        assert len(usuarios) == 3  # admin + 2

    def test_verificar_contrasena_correcta(self, db_tmp):
        """Contraseña correcta retorna True."""
        crear_usuario("v@test.com", "MiPass123!", "V", "negocio", ruta_bd=db_tmp)
        usuario = obtener_usuario_por_correo("v@test.com", db_tmp)
        assert verificar_contrasena("MiPass123!", usuario["contrasena_hash"]) is True

    def test_verificar_contrasena_incorrecta(self, db_tmp):
        """Contraseña incorrecta retorna False."""
        crear_usuario("w@test.com", "CorrectPass!", "W", "ti", ruta_bd=db_tmp)
        usuario = obtener_usuario_por_correo("w@test.com", db_tmp)
        assert verificar_contrasena("WrongPass!", usuario["contrasena_hash"]) is False

    def test_cambiar_contrasena(self, db_tmp):
        """Cambiar contraseña y verificar con la nueva."""
        uid = crear_usuario("c@test.com", "Old123!", "C", "negocio", ruta_bd=db_tmp)
        cambiar_contrasena(uid, "New456!", db_tmp)
        usuario = obtener_usuario_por_id(uid, db_tmp)
        assert verificar_contrasena("New456!", usuario["contrasena_hash"]) is True
        assert verificar_contrasena("Old123!", usuario["contrasena_hash"]) is False

    def test_cambiar_estado_usuario(self, db_tmp):
        """Desactivar y reactivar un usuario."""
        uid = crear_usuario("e@test.com", "P!", "E", "negocio", ruta_bd=db_tmp)

        # Desactivar
        resultado = cambiar_estado_usuario(uid, False, db_tmp)
        assert resultado is True
        usuario = obtener_usuario_por_id(uid, db_tmp)
        assert usuario["activo"] == 0

        # Reactivar
        cambiar_estado_usuario(uid, True, db_tmp)
        usuario = obtener_usuario_por_id(uid, db_tmp)
        assert usuario["activo"] == 1

    def test_obtener_usuario_inexistente(self, db_tmp):
        """Buscar usuario que no existe retorna None."""
        assert obtener_usuario_por_correo("noexiste@test.com", db_tmp) is None
        assert obtener_usuario_por_id(9999, db_tmp) is None


# =============================================================================
# TESTS — CRUD CARGAS
# =============================================================================

class TestCrudCargas:
    def test_crear_carga(self, db_tmp):
        """Crear una carga y verificar datos."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        carga_id = crear_carga(
            usuario_id=admin["id"],
            nombre_archivo="precios_marzo.xlsx",
            total_filas=150,
            total_errores=3,
            resultado_validacion={"resumen": {"es_valido_global": False}},
            ruta_bd=db_tmp,
        )
        assert carga_id > 0

        carga = obtener_carga_por_id(carga_id, db_tmp)
        assert carga["nombre_archivo"] == "precios_marzo.xlsx"
        assert carga["estado"] == "validando"
        assert carga["total_filas"] == 150
        assert carga["total_errores"] == 3
        assert carga["resultado_validacion"]["resumen"]["es_valido_global"] is False

    def test_listar_cargas_por_usuario(self, db_tmp):
        """Verificar que solo se listan las cargas del usuario."""
        uid1 = crear_usuario("u1@t.com", "P!", "U1", "negocio", ruta_bd=db_tmp)
        uid2 = crear_usuario("u2@t.com", "P!", "U2", "negocio", ruta_bd=db_tmp)

        crear_carga(uid1, "file1.xlsx", ruta_bd=db_tmp)
        crear_carga(uid1, "file2.xlsx", ruta_bd=db_tmp)
        crear_carga(uid2, "file3.xlsx", ruta_bd=db_tmp)

        cargas_u1 = listar_cargas_por_usuario(uid1, db_tmp)
        assert len(cargas_u1) == 2

        cargas_u2 = listar_cargas_por_usuario(uid2, db_tmp)
        assert len(cargas_u2) == 1

    def test_actualizar_estado_a_aprobado(self, db_tmp):
        """Aprobar una carga cambia estado y registra fecha."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        carga_id = crear_carga(admin["id"], "test.xlsx", ruta_bd=db_tmp)

        resultado = actualizar_estado_carga(carga_id, "aprobado", ruta_bd=db_tmp)
        assert resultado is True

        carga = obtener_carga_por_id(carga_id, db_tmp)
        assert carga["estado"] == "aprobado"
        assert carga["fecha_aprobacion"] is not None

    def test_actualizar_estado_a_cargado_bd(self, db_tmp):
        """Cargar a BD registra estado, fecha y usuario TI."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        ti_id = crear_usuario("ti@t.com", "P!", "TI", "ti", ruta_bd=db_tmp)
        carga_id = crear_carga(admin["id"], "test.xlsx", ruta_bd=db_tmp)

        actualizar_estado_carga(carga_id, "aprobado", ruta_bd=db_tmp)
        actualizar_estado_carga(
            carga_id, "cargado_bd", usuario_ti_id=ti_id, ruta_bd=db_tmp
        )

        carga = obtener_carga_por_id(carga_id, db_tmp)
        assert carga["estado"] == "cargado_bd"
        assert carga["fecha_carga_bd"] is not None
        assert carga["usuario_ti_id"] == ti_id

    def test_listar_cargas_por_estado(self, db_tmp):
        """Filtrar cargas por estado."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        c1 = crear_carga(admin["id"], "f1.xlsx", ruta_bd=db_tmp)
        c2 = crear_carga(admin["id"], "f2.xlsx", ruta_bd=db_tmp)
        crear_carga(admin["id"], "f3.xlsx", ruta_bd=db_tmp)

        actualizar_estado_carga(c1, "aprobado", ruta_bd=db_tmp)
        actualizar_estado_carga(c2, "aprobado", ruta_bd=db_tmp)

        aprobadas = listar_cargas_por_estado("aprobado", db_tmp)
        assert len(aprobadas) == 2

        validando = listar_cargas_por_estado("validando", db_tmp)
        assert len(validando) == 1

    def test_obtener_carga_inexistente(self, db_tmp):
        """Buscar carga que no existe retorna None."""
        assert obtener_carga_por_id(9999, db_tmp) is None


# =============================================================================
# TESTS — BITÁCORA DE ACCIONES
# =============================================================================

class TestBitacora:
    def test_registrar_accion(self, db_tmp):
        """Registrar una acción y verificar que se guarda."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        accion_id = registrar_accion(
            usuario_id=admin["id"],
            accion="login",
            detalle="Inicio de sesión exitoso",
            ruta_bd=db_tmp,
        )
        assert accion_id > 0

    def test_listar_bitacora(self, db_tmp):
        """Listar bitácora retorna las últimas acciones."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        registrar_accion(admin["id"], "login", ruta_bd=db_tmp)
        registrar_accion(admin["id"], "crear_usuario", detalle="Creó u1@t.com",
                         tabla_afectada="usuarios", registro_id=2, ruta_bd=db_tmp)

        bitacora = listar_bitacora(ruta_bd=db_tmp)
        assert len(bitacora) == 2
        assert bitacora[0]["accion"] == "crear_usuario"  # más reciente primero
        assert bitacora[0]["usuario_nombre"] == "Administrador"

    def test_listar_bitacora_por_usuario(self, db_tmp):
        """Filtrar bitácora por usuario."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        uid = crear_usuario("x@t.com", "P!", "X", "negocio", ruta_bd=db_tmp)

        registrar_accion(admin["id"], "admin_action", ruta_bd=db_tmp)
        registrar_accion(uid, "user_action", ruta_bd=db_tmp)

        bitacora_admin = listar_bitacora_por_usuario(admin["id"], ruta_bd=db_tmp)
        assert len(bitacora_admin) == 1
        assert bitacora_admin[0]["accion"] == "admin_action"

    def test_registrar_accion_con_tabla_y_registro(self, db_tmp):
        """Registrar acción con tabla afectada y registro ID."""
        admin = obtener_usuario_por_correo("admin@fastrack.com", db_tmp)
        registrar_accion(
            usuario_id=admin["id"],
            accion="aprobar_carga",
            detalle="Aprobó carga de precios marzo",
            tabla_afectada="cargas",
            registro_id=1,
            ruta_bd=db_tmp,
        )
        bitacora = listar_bitacora(ruta_bd=db_tmp)
        assert bitacora[0]["tabla_afectada"] == "cargas"
        assert bitacora[0]["registro_id"] == 1
