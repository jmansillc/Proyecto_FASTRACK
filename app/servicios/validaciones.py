"""
Módulo de Validaciones — Proyecto Fastrack
==========================================

Contiene funciones de validación de calidad de datos para archivos Excel
de precios residenciales. Cada función recibe un DataFrame de pandas y
retorna un diccionario con el resultado de la validación.

Convenciones:
    - Nombres de funciones y variables en español.
    - Cada función retorna un dict con la clave "es_valido" (bool).
    - Los errores incluyen detalle de filas afectadas (máx. 20 ejemplos).

Uso:
    from app.servicios.validaciones import validar_nulos, validar_precio
"""

import pandas as pd
from io import BytesIO
from typing import Optional


# =============================================================================
# CONSTANTES
# =============================================================================

MAXIMO_FILAS_EJEMPLO = 20
"""Cantidad máxima de filas de ejemplo a incluir en los reportes de error."""

OFFSET_FILA_EXCEL = 2
"""Offset para convertir índice DataFrame (0-based) a fila Excel (1-based + header)."""


def _fila_excel(indice: int) -> int:
    """Convierte un índice de DataFrame a número de fila en Excel."""
    return indice + OFFSET_FILA_EXCEL


# =============================================================================
# VALIDACIONES DE ESTRUCTURA
# =============================================================================

def validar_estructura_excel(
    contenido: bytes,
    nombre_hoja: str,
    columnas_requeridas: list
) -> dict:
    """
    Valida que el archivo Excel tenga la hoja esperada y todas las columnas
    requeridas antes de proceder con las demás validaciones.

    Parámetros:
        contenido (bytes): Contenido binario del archivo Excel.
        nombre_hoja (str): Nombre de la hoja que debe existir.
        columnas_requeridas (list): Lista de nombres de columna obligatorios.

    Retorna:
        dict: Resultado con claves 'es_valido', 'total_columnas',
              'total_filas', y 'error' si aplica.
    """
    try:
        archivo_excel = pd.ExcelFile(BytesIO(contenido), engine="openpyxl")
    except Exception as excepcion:
        return {
            "es_valido": False,
            "error": f"No se pudo leer el archivo Excel: {str(excepcion)}"
        }

    # Verificar que la hoja exista
    if nombre_hoja not in archivo_excel.sheet_names:
        return {
            "es_valido": False,
            "error": (
                f"La hoja '{nombre_hoja}' no fue encontrada. "
                f"Hojas disponibles: {archivo_excel.sheet_names}"
            )
        }

    # Leer la hoja y verificar columnas
    df = pd.read_excel(archivo_excel, sheet_name=nombre_hoja)
    columnas_faltantes = sorted(
        set(columnas_requeridas) - set(df.columns)
    )

    if columnas_faltantes:
        return {
            "es_valido": False,
            "error": f"Columnas faltantes en el archivo: {columnas_faltantes}"
        }

    return {
        "es_valido": True,
        "total_columnas": len(df.columns),
        "total_filas": len(df)
    }


# =============================================================================
# VALIDACIÓN DE VALORES NULOS
# =============================================================================

def validar_nulos(df: pd.DataFrame, columnas_obligatorias: list) -> dict:
    """
    Verifica que las columnas obligatorias no contengan valores nulos (NaN).

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columnas_obligatorias (list): Columnas que no deben tener nulos.

    Retorna:
        dict: Resultado con detalle de filas nulas por columna.
              Incluye las posiciones exactas de las filas afectadas.
    """
    errores = {}

    for columna in columnas_obligatorias:
        # Verificar que la columna exista en el DataFrame
        if columna not in df.columns:
            errores[columna] = {
                "mensaje": "La columna no existe en el archivo",
                "cantidad": 0,
                "filas": []
            }
            continue

        # Buscar filas con valores nulos
        mascara_nulos = df[columna].isnull()
        cantidad_nulos = mascara_nulos.sum()

        if cantidad_nulos > 0:
            filas_afectadas = df.index[mascara_nulos].tolist()
            filas_excel = [
                {"fila_excel": _fila_excel(i), "valor": "(vacío)"}
                for i in filas_afectadas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores[columna] = {
                "mensaje": f"{cantidad_nulos} valores nulos encontrados",
                "cantidad": int(cantidad_nulos),
                "filas": filas_afectadas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel
            }

    return {
        "nombre_validacion": "Valores Nulos",
        "total_registros": len(df),
        "columnas_validadas": columnas_obligatorias,
        "errores": errores,
        "es_valido": len(errores) == 0
    }


# =============================================================================
# VALIDACIÓN DE VALORES ÚNICOS
# =============================================================================

def validar_unicos(df: pd.DataFrame, columnas_valor_unico: list) -> dict:
    """
    Verifica que ciertas columnas contengan un solo valor distinto
    en todo el archivo (por ejemplo, MONEDA siempre debe ser "COP").

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columnas_valor_unico (list): Columnas que deben tener un solo
                                      valor único en todo el archivo.

    Retorna:
        dict: Resultado con detalle de cuántos valores distintos se
              encontraron y cuáles son.
    """
    errores = {}

    for columna in columnas_valor_unico:
        # Verificar que la columna exista en el DataFrame
        if columna not in df.columns:
            errores[columna] = {
                "mensaje": "La columna no existe en el archivo",
                "valores_encontrados": []
            }
            continue

        # Contar valores distintos (excluyendo nulos)
        valores_distintos = df[columna].dropna().unique().tolist()
        cantidad_unicos = len(valores_distintos)

        if cantidad_unicos > 1:
            errores[columna] = {
                "mensaje": f"Se esperaba 1 valor único, se encontraron {cantidad_unicos}",
                "valores_encontrados": valores_distintos[:MAXIMO_FILAS_EJEMPLO]
            }

    return {
        "nombre_validacion": "Valores Únicos",
        "total_registros": len(df),
        "columnas_validadas": columnas_valor_unico,
        "errores": errores,
        "es_valido": len(errores) == 0
    }


# =============================================================================
# VALIDACIÓN DE PRECIOS
# =============================================================================

def validar_precio(
    df: pd.DataFrame,
    columnas_precio: list,
    precio_minimo: float = 0,
    precio_maximo: float = 999999
) -> dict:
    """
    Verifica que las columnas de precio contengan valores numéricos válidos,
    no negativos, y dentro de un rango razonable.

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columnas_precio (list): Columnas que deben contener precios.
        precio_minimo (float): Valor mínimo aceptable (default: 0).
        precio_maximo (float): Valor máximo aceptable (default: 999999).

    Retorna:
        dict: Resultado con detalle de errores por tipo (no numérico,
              negativo, fuera de rango) para cada columna.
    """
    errores = {}

    for columna in columnas_precio:
        # Verificar que la columna exista en el DataFrame
        if columna not in df.columns:
            errores[columna] = {
                "mensaje": "La columna no existe en el archivo",
                "detalle": {}
            }
            continue

        serie_original = df[columna]
        serie_numerica = pd.to_numeric(serie_original, errors="coerce")
        errores_columna = {}

        # Detectar valores no numéricos
        mascara_no_numerico = serie_numerica.isna() & serie_original.notna()
        if mascara_no_numerico.any():
            filas = df.index[mascara_no_numerico].tolist()
            filas_excel = [
                {"fila_excel": _fila_excel(i), "valor": str(serie_original.iloc[i]) if i < len(serie_original) else "?"}
                for i in filas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores_columna["no_numerico"] = {
                "mensaje": f"{mascara_no_numerico.sum()} valores no numéricos",
                "cantidad": int(mascara_no_numerico.sum()),
                "filas": filas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel
            }

        # Detectar precios negativos
        mascara_negativos = serie_numerica < 0
        if mascara_negativos.any():
            filas = df.index[mascara_negativos].tolist()
            filas_excel = [
                {"fila_excel": _fila_excel(i), "valor": str(serie_original.iloc[i]) if i < len(serie_original) else "?"}
                for i in filas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores_columna["negativos"] = {
                "mensaje": f"{mascara_negativos.sum()} precios negativos",
                "cantidad": int(mascara_negativos.sum()),
                "filas": filas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel
            }

        # Detectar precios fuera de rango
        mascara_fuera_rango = (serie_numerica > precio_maximo)
        if mascara_fuera_rango.any():
            filas = df.index[mascara_fuera_rango].tolist()
            filas_excel = [
                {"fila_excel": _fila_excel(i), "valor": str(serie_original.iloc[i]) if i < len(serie_original) else "?"}
                for i in filas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores_columna["fuera_de_rango"] = {
                "mensaje": (
                    f"{mascara_fuera_rango.sum()} precios superan "
                    f"el máximo permitido ({precio_maximo})"
                ),
                "cantidad": int(mascara_fuera_rango.sum()),
                "filas": filas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel,
                "maximo_encontrado": float(serie_numerica.max())
            }

        if errores_columna:
            errores[columna] = {
                "mensaje": f"{columna} tiene errores de precio",
                "detalle": errores_columna
            }

    return {
        "nombre_validacion": "Formato y Rango de Precios",
        "total_registros": len(df),
        "columnas_validadas": columnas_precio,
        "errores": errores,
        "es_valido": len(errores) == 0
    }


# =============================================================================
# VALIDACIÓN DE FECHAS
# =============================================================================

def validar_fecha(
    df: pd.DataFrame,
    columnas_fecha: list,
    formato_fecha: str = "%d/%m/%Y"
) -> dict:
    """
    Verifica que las columnas de fecha contengan valores con el formato
    esperado (por defecto dd/mm/yyyy).

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columnas_fecha (list): Columnas que deben contener fechas.
        formato_fecha (str): Formato esperado (default: "%d/%m/%Y").

    Retorna:
        dict: Resultado con detalle de filas con formato inválido.
    """
    errores = {}

    for columna in columnas_fecha:
        # Verificar que la columna exista en el DataFrame
        if columna not in df.columns:
            errores[columna] = {
                "mensaje": "La columna no existe en el archivo",
                "cantidad": 0,
                "filas": []
            }
            continue

        serie_fecha = df[columna]

        # Intentar convertir al formato esperado
        fechas_convertidas = pd.to_datetime(
            serie_fecha,
            format=formato_fecha,
            errors="coerce"
        )

        # Filas que no se pudieron convertir (excluyendo nulos originales)
        mascara_invalidas = fechas_convertidas.isna() & serie_fecha.notna()

        if mascara_invalidas.any():
            filas_afectadas = df.index[mascara_invalidas].tolist()
            filas_excel = [
                {"fila_excel": _fila_excel(i), "valor": str(serie_fecha.iloc[i]) if i < len(serie_fecha) else "?"}
                for i in filas_afectadas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores[columna] = {
                "mensaje": (
                    f"{mascara_invalidas.sum()} valores no cumplen "
                    f"el formato de fecha ({formato_fecha})"
                ),
                "cantidad": int(mascara_invalidas.sum()),
                "filas": filas_afectadas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel
            }

    return {
        "nombre_validacion": "Formato de Fechas",
        "total_registros": len(df),
        "columnas_validadas": columnas_fecha,
        "errores": errores,
        "es_valido": len(errores) == 0
    }


# =============================================================================
# VALIDACIÓN DE DUPLICADOS
# =============================================================================

def validar_duplicados(df: pd.DataFrame, columnas_clave: list) -> dict:
    """
    Detecta filas duplicadas basándose en una combinación de columnas clave.
    Incluye un resumen agrupado de las combinaciones repetidas.

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columnas_clave (list): Columnas que forman la clave de unicidad.

    Retorna:
        dict: Resultado con total de duplicados, combinaciones afectadas,
              y las filas específicas donde ocurren.
    """
    # Verificar que todas las columnas clave existan
    columnas_faltantes = [c for c in columnas_clave if c not in df.columns]
    if columnas_faltantes:
        return {
            "nombre_validacion": "Filas Duplicadas",
            "total_registros": len(df),
            "columnas_clave": columnas_clave,
            "error": f"Columnas clave faltantes: {columnas_faltantes}",
            "es_valido": False
        }

    # Identificar filas duplicadas (mantener todas las ocurrencias)
    duplicados_df = df[df.duplicated(subset=columnas_clave, keep=False)]
    total_duplicados = len(duplicados_df)

    # Resumen agrupado por combinación de clave
    resumen = (
        duplicados_df
        .groupby(columnas_clave)
        .size()
        .reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)
    )

    # Convertir NaN a None para serialización JSON segura
    ejemplo_list = resumen.head(10).where(resumen.head(10).notna(), None).to_dict(orient="records")

    filas_excel_duplicadas = [
        _fila_excel(i) for i in duplicados_df.index.tolist()[:MAXIMO_FILAS_EJEMPLO]
    ]

    return {
        "nombre_validacion": "Filas Duplicadas",
        "total_registros": len(df),
        "columnas_clave": columnas_clave,
        "total_filas_duplicadas": total_duplicados,
        "total_combinaciones_duplicadas": len(resumen),
        "ejemplo_duplicados": ejemplo_list,
        "filas_duplicadas": duplicados_df.index.tolist()[:MAXIMO_FILAS_EJEMPLO],
        "filas_excel_duplicadas": filas_excel_duplicadas,
        "es_valido": total_duplicados == 0
    }



# =============================================================================
# VALIDACIÓN DE COHERENCIA DE FECHAS
# =============================================================================

def validar_coherencia_fechas(
    df: pd.DataFrame,
    columna_inicio: str = "FECHA_EFECTIVA",
    columna_fin: str = "FECHA_FIN",
    formato_fecha: str = "%d/%m/%Y"
) -> dict:
    """
    Verifica que la fecha de fin sea posterior o igual a la fecha de inicio
    en cada fila. Detecta filas donde las fechas están invertidas.

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columna_inicio (str): Nombre de la columna de fecha de inicio.
        columna_fin (str): Nombre de la columna de fecha de fin.
        formato_fecha (str): Formato esperado de las fechas.

    Retorna:
        dict: Resultado con filas donde la fecha de fin es anterior
              a la fecha de inicio.
    """
    # Verificar que ambas columnas existan
    for columna in [columna_inicio, columna_fin]:
        if columna not in df.columns:
            return {
                "nombre_validacion": "Coherencia de Fechas",
                "total_registros": len(df),
                "error": f"La columna '{columna}' no existe en el archivo",
                "es_valido": False
            }

    # Convertir fechas
    fecha_inicio = pd.to_datetime(
        df[columna_inicio], format=formato_fecha, errors="coerce"
    )
    fecha_fin = pd.to_datetime(
        df[columna_fin], format=formato_fecha, errors="coerce"
    )

    # Detectar filas donde fin < inicio (solo si ambas son válidas)
    mascara_ambas_validas = fecha_inicio.notna() & fecha_fin.notna()
    mascara_invertidas = (fecha_fin < fecha_inicio) & mascara_ambas_validas
    filas_invertidas = df.index[mascara_invertidas].tolist()

    filas_excel = [
        {
            "fila_excel": _fila_excel(i),
            "fecha_inicio": str(df[columna_inicio].iloc[i]),
            "fecha_fin": str(df[columna_fin].iloc[i])
        }
        for i in filas_invertidas[:MAXIMO_FILAS_EJEMPLO]
    ]

    return {
        "nombre_validacion": "Coherencia de Fechas",
        "total_registros": len(df),
        "columnas_validadas": [columna_inicio, columna_fin],
        "total_filas_invertidas": len(filas_invertidas),
        "filas_invertidas": filas_invertidas[:MAXIMO_FILAS_EJEMPLO],
        "filas_excel": filas_excel,
        "es_valido": len(filas_invertidas) == 0
    }


# =============================================================================
# VALIDACIÓN DE ESCALAMIENTO DE PRECIOS
# =============================================================================

def validar_escalamiento_precios(
    df: pd.DataFrame,
    columnas_precio_ordenadas: Optional[list] = None
) -> dict:
    """
    Verifica que los precios escalonados por plazo mantengan una
    relación consistente (el precio a mayor plazo no debería ser menor
    que el precio a menor plazo).

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columnas_precio_ordenadas (list): Lista ordenada de columnas de
            precio por plazo (de menor a mayor). Si no se proporciona,
            usa el orden predeterminado.

    Retorna:
        dict: Resultado con filas que presentan inconsistencias en
              el escalamiento de precios.
    """
    if columnas_precio_ordenadas is None:
        columnas_precio_ordenadas = [
            "PRECIO_0M", "PRECIO_6M", "PRECIO_12M",
            "PRECIO_18M", "PRECIO_24M", "PRECIO_36M"
        ]

    # Verificar que las columnas existan
    columnas_faltantes = [
        c for c in columnas_precio_ordenadas if c not in df.columns
    ]
    if columnas_faltantes:
        return {
            "nombre_validacion": "Escalamiento de Precios",
            "total_registros": len(df),
            "error": f"Columnas faltantes: {columnas_faltantes}",
            "es_valido": False
        }

    inconsistencias = []

    for indice, fila in df.iterrows():
        precios = [
            pd.to_numeric(fila.get(col), errors="coerce")
            for col in columnas_precio_ordenadas
        ]

        # Saltar filas con valores no numéricos
        if any(pd.isna(precio) for precio in precios):
            continue

        # Comparar cada precio con el siguiente
        for i in range(1, len(precios)):
            if precios[i] < precios[i - 1]:
                inconsistencias.append({
                    "fila": int(indice),
                    "fila_excel": _fila_excel(int(indice)),
                    "columna_menor": columnas_precio_ordenadas[i],
                    "valor_menor": float(precios[i]),
                    "columna_mayor": columnas_precio_ordenadas[i - 1],
                    "valor_mayor": float(precios[i - 1])
                })
                break  # Reportar solo la primera inconsistencia por fila

    return {
        "nombre_validacion": "Escalamiento de Precios",
        "total_registros": len(df),
        "columnas_validadas": columnas_precio_ordenadas,
        "total_inconsistencias": len(inconsistencias),
        "inconsistencias": inconsistencias[:MAXIMO_FILAS_EJEMPLO],
        "es_valido": len(inconsistencias) == 0
    }


# =============================================================================
# VALIDACIÓN DE ESPACIOS EN BLANCO
# =============================================================================

def validar_espacios_en_blanco(
    df: pd.DataFrame,
    columnas_texto: list
) -> dict:
    """
    Detecta valores con espacios en blanco al inicio o al final que
    podrían causar errores de coincidencia o búsqueda en sistemas
    downstream.

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        columnas_texto (list): Columnas de texto a revisar.

    Retorna:
        dict: Resultado con columnas que contienen valores con
              espacios ocultos y la cantidad de filas afectadas.
    """
    errores = {}

    for columna in columnas_texto:
        # Verificar que la columna exista y sea de tipo texto
        if columna not in df.columns:
            errores[columna] = {
                "mensaje": "La columna no existe en el archivo",
                "cantidad": 0
            }
            continue

        if not pd.api.types.is_string_dtype(df[columna]):
            continue  # No es columna de texto, saltar

        # Comparar valor original vs. valor sin espacios laterales
        serie_texto = df[columna].dropna().astype(str)
        serie_limpia = serie_texto.str.strip()
        mascara_con_espacios = serie_texto.ne(serie_limpia)
        cantidad = mascara_con_espacios.sum()

        if cantidad > 0:
            filas = serie_texto.index[mascara_con_espacios].tolist()
            filas_excel = [
                {"fila_excel": _fila_excel(i), "valor": repr(serie_texto.loc[i])}
                for i in filas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores[columna] = {
                "mensaje": (
                    f"{cantidad} valores tienen espacios "
                    f"al inicio o al final"
                ),
                "cantidad": int(cantidad),
                "filas": filas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel
            }

    return {
        "nombre_validacion": "Espacios en Blanco Ocultos",
        "total_registros": len(df),
        "columnas_validadas": columnas_texto,
        "errores": errores,
        "es_valido": len(errores) == 0
    }


# =============================================================================
# VALIDACIÓN DE LONGITUD DE TEXTO
# =============================================================================

def validar_longitud(
    df: pd.DataFrame,
    longitudes_maximas: dict
) -> dict:
    """
    Verifica que los valores de texto no excedan la longitud máxima
    configurada para cada columna.

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        longitudes_maximas (dict): Diccionario {columna: longitud_maxima}.

    Retorna:
        dict: Resultado con detalle de filas que exceden la longitud máxima.
    """
    errores = {}

    for columna, max_len in longitudes_maximas.items():
        if columna not in df.columns:
            continue

        serie = df[columna].dropna().astype(str)
        longitudes = serie.str.len()
        mascara_excede = longitudes > max_len

        if mascara_excede.any():
            filas = serie.index[mascara_excede].tolist()
            cantidad = int(mascara_excede.sum())
            filas_excel = [
                {
                    "fila_excel": _fila_excel(i),
                    "valor": str(serie.loc[i])[:60],
                    "longitud": int(longitudes.loc[i]),
                    "maximo": max_len,
                }
                for i in filas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores[columna] = {
                "mensaje": (
                    f"{cantidad} valores exceden la longitud máxima "
                    f"de {max_len} caracteres"
                ),
                "cantidad": cantidad,
                "longitud_maxima_permitida": max_len,
                "filas": filas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel,
            }

    return {
        "nombre_validacion": "Longitud de Texto",
        "total_registros": len(df),
        "columnas_validadas": list(longitudes_maximas.keys()),
        "errores": errores,
        "es_valido": len(errores) == 0
    }


# =============================================================================
# VALIDACIÓN DE VALORES PERMITIDOS
# =============================================================================

def validar_valores_permitidos(
    df: pd.DataFrame,
    valores_permitidos: dict
) -> dict:
    """
    Verifica que los valores de cada columna estén dentro del conjunto
    de valores permitidos.

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos a validar.
        valores_permitidos (dict): Diccionario {columna: [lista_valores_validos]}.

    Retorna:
        dict: Resultado con detalle de filas con valores no permitidos.
    """
    errores = {}

    for columna, validos in valores_permitidos.items():
        if columna not in df.columns:
            continue

        serie = df[columna].dropna().astype(str).str.strip()
        validos_str = [str(v).strip() for v in validos]
        mascara_invalido = ~serie.isin(validos_str)

        if mascara_invalido.any():
            filas = serie.index[mascara_invalido].tolist()
            cantidad = int(mascara_invalido.sum())
            valores_encontrados = serie[mascara_invalido].unique().tolist()[:10]
            filas_excel = [
                {
                    "fila_excel": _fila_excel(i),
                    "valor": str(serie.loc[i])[:60],
                }
                for i in filas[:MAXIMO_FILAS_EJEMPLO]
            ]
            errores[columna] = {
                "mensaje": (
                    f"{cantidad} valores no están en la lista permitida: "
                    f"{', '.join(validos_str)}"
                ),
                "cantidad": cantidad,
                "valores_permitidos": validos_str,
                "valores_encontrados": valores_encontrados,
                "filas": filas[:MAXIMO_FILAS_EJEMPLO],
                "filas_excel": filas_excel,
            }

    return {
        "nombre_validacion": "Valores Permitidos",
        "total_registros": len(df),
        "columnas_validadas": list(valores_permitidos.keys()),
        "errores": errores,
        "es_valido": len(errores) == 0
    }
