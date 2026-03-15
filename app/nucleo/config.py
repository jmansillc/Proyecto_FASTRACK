"""
Configuración de Validaciones — Proyecto Fastrack
==================================================

Define las listas de columnas y parámetros que se utilizan en cada
tipo de validación. Centraliza toda la configuración del motor para
facilitar cambios sin modificar el código de validación.

Uso:
    from app.nucleo.config import NOMBRE_HOJA, COLUMNAS_PRECIO
"""


# =============================================================================
# NOMBRE DE LA HOJA ESPERADA EN EL EXCEL
# =============================================================================

NOMBRE_HOJA = "GENERICA_RESIDENCIAL"
"""Nombre de la hoja que debe existir en el archivo Excel."""


# =============================================================================
# TAMAÑO MÁXIMO DE ARCHIVO (EN MEGABYTES)
# =============================================================================

TAMANO_MAXIMO_MB = 50
"""Tamaño máximo permitido del archivo Excel en megabytes."""


# =============================================================================
# LISTAS DE COLUMNAS POR TIPO DE VALIDACIÓN
# =============================================================================

COLUMNAS_CLAVE = [
    "Modelo",
    "FORMA DE PAGO",
    "TRANSACCION",
    "GRUPO_PLAN"
]
"""Columnas que forman la clave de unicidad para detectar duplicados."""

COLUMNAS_OBLIGATORIAS = [
    "DETALLE CAMBIO", "Modelo", "FORMA DE PAGO", "TRANSACCION",
    "GRUPO_PLAN", "RANGOS", "SEGMENTO", "GRUPO_VALOR_SUBSCRIPCION",
    "SUBTIPO_CLIENTE", "FECHA_EFECTIVA", "PRECIO_0M", "MONEDA",
    "PRECIO_6M", "PRECIO_12M", "PRECIO_18M", "PRECIO_24M",
    "PRECIO_36M", "FECHA_FIN", "TIPO", "TARIFA_SOCIAL",
    "Precio Lista", "PL"
]
"""Columnas que no deben contener valores nulos."""

COLUMNAS_VALOR_UNICO = [
    "SEGMENTO",
    "MONEDA",
    "TARIFA_SOCIAL"
]
"""Columnas que deben tener un solo valor distinto en todo el archivo."""

COLUMNAS_PRECIO = [
    "PRECIO_0M", "PRECIO_6M", "PRECIO_12M",
    "PRECIO_18M", "PRECIO_24M", "PRECIO_36M",
    "Precio Lista"
]
"""Columnas que deben contener valores numéricos de precio."""

COLUMNAS_PRECIO_ESCALONADAS = [
    "PRECIO_0M", "PRECIO_6M", "PRECIO_12M",
    "PRECIO_18M", "PRECIO_24M", "PRECIO_36M"
]
"""Columnas de precio ordenadas por plazo para validar escalamiento."""

COLUMNAS_FECHA = [
    "FECHA_EFECTIVA",
    "FECHA_FIN"
]
"""Columnas que deben contener fechas en formato dd/mm/yyyy."""

COLUMNAS_TEXTO = [
    "Modelo", "FORMA DE PAGO", "TRANSACCION",
    "GRUPO_PLAN", "SEGMENTO", "SUBTIPO_CLIENTE",
    "TIPO", "TARIFA_SOCIAL", "DETALLE CAMBIO"
]
"""Columnas de texto donde se revisan espacios ocultos."""


# =============================================================================
# REGLAS DE RANGO DE PRECIOS
# =============================================================================

PRECIO_MINIMO = 0
"""Valor mínimo aceptable para un precio."""

PRECIO_MAXIMO = 999999
"""Valor máximo aceptable para un precio."""


# =============================================================================
# FORMATO DE FECHAS
# =============================================================================

FORMATO_FECHA = "%d/%m/%Y"
"""Formato esperado para las columnas de tipo fecha."""


# =============================================================================
# VALORES FIJOS — Columnas que siempre deben tener un único valor conocido
# =============================================================================

VALORES_FIJOS = {
    "SEGMENTO": "R",
    "MONEDA": "PEN",
    "TARIFA_SOCIAL": "NO",
}
"""Valor esperado para cada columna fija. Si llega otro valor se auto-corrige."""


# =============================================================================
# VALORES PERMITIDOS — Columnas con un conjunto acotado de valores válidos
# =============================================================================

VALORES_PERMITIDOS = {
    "SUBTIPO_CLIENTE": ["CNA", "NA"],
    "GRUPO_VALOR_SUBSCRIPCION": ["POS1", "POS2", "POS3", "NA"],
    "FORMA DE PAGO": [
        "TELEF001", "TELEF002", "TELEF003", "TELEF004",
        "TELEF005", "TELEF006", "TELEFCONT",
    ],
}
"""Valores válidos para cada columna. Si llega un valor diferente, se reporta como error."""


# =============================================================================
# LONGITUDES MÁXIMAS — Límite de caracteres por columna de texto
# =============================================================================

LONGITUDES_MAXIMAS = {
    "DETALLE CAMBIO": 10,
    "Modelo": 50,
    "FORMA DE PAGO": 12,
    "TRANSACCION": 25,
    "GRUPO_PLAN": 12,
    "RANGOS": 30,
    "SEGMENTO": 5,
    "GRUPO_VALOR_SUBSCRIPCION": 6,
    "SUBTIPO_CLIENTE": 5,
    "MONEDA": 5,
    "TIPO": 25,
    "TARIFA_SOCIAL": 5,
}
"""Longitud máxima permitida para cada columna de texto."""


# =============================================================================
# TODAS LAS COLUMNAS REQUERIDAS (unión para validación de estructura)
# =============================================================================

COLUMNAS_REQUERIDAS = sorted(set(
    COLUMNAS_CLAVE + COLUMNAS_OBLIGATORIAS +
    COLUMNAS_PRECIO + COLUMNAS_FECHA
))
"""Lista completa de todas las columnas que deben existir en el archivo."""


# =============================================================================
# BASE DE DATOS
# =============================================================================

import os as _os

RUTA_BD = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
    "fastrack.db",
)
"""Ruta al archivo SQLite de la base de datos."""

ADMIN_CORREO = "admin@fastrack.com"
"""Correo del usuario administrador por defecto."""

ADMIN_NOMBRE = "Administrador"
"""Nombre del usuario administrador por defecto."""

ADMIN_CONTRASENA = "Admin123!"
"""Contraseña inicial del administrador (cambiar tras primer login)."""
