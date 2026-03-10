"""
Módulo de Auto-corrección — Proyecto Fastrack
==============================================

Contiene la lógica para corregir automáticamente columnas de valor fijo
cuando se detecta un valor distinto al esperado. Genera un reporte de
las correcciones realizadas para que el usuario sepa qué se modificó.

Uso:
    from app.servicios.correcciones import autocorregir_valores_fijos
"""

import pandas as pd
from typing import Tuple

OFFSET_FILA_EXCEL = 2
"""Offset para convertir índice DataFrame (0-based) a fila Excel (1-based + header)."""

MAXIMO_FILAS_REPORTE = 200
"""Cantidad máxima de correcciones a incluir en el reporte."""


def _fila_excel(indice: int) -> int:
    """Convierte un índice de DataFrame a número de fila en Excel."""
    return indice + OFFSET_FILA_EXCEL


def autocorregir_valores_fijos(
    df: pd.DataFrame,
    valores_fijos: dict
) -> Tuple[pd.DataFrame, dict]:
    """
    Corrige automáticamente columnas que deben tener un valor fijo.
    Si una celda tiene un valor distinto al esperado, se reemplaza
    por el valor correcto.

    Parámetros:
        df (pd.DataFrame): DataFrame con los datos (se modifica una copia).
        valores_fijos (dict): Diccionario {columna: valor_esperado}.

    Retorna:
        tuple: (df_corregido, reporte)
            - df_corregido: DataFrame con las correcciones aplicadas.
            - reporte: dict con detalle de las correcciones realizadas.
    """
    df_corregido = df.copy()
    correcciones = []
    resumen_por_columna = {}

    for columna, valor_esperado in valores_fijos.items():
        if columna not in df_corregido.columns:
            continue

        # Encontrar filas con valor distinto al esperado (excluyendo nulos)
        serie = df_corregido[columna]
        mascara_no_nulo = serie.notna()
        mascara_distinto = mascara_no_nulo & (serie.astype(str).str.strip() != str(valor_esperado))

        filas_afectadas = df_corregido.index[mascara_distinto].tolist()

        if len(filas_afectadas) == 0:
            continue

        # Registrar cada corrección
        for i in filas_afectadas[:MAXIMO_FILAS_REPORTE]:
            valor_original = serie.iloc[i]
            correcciones.append({
                "fila_excel": _fila_excel(i),
                "columna": columna,
                "valor_original": str(valor_original),
                "valor_corregido": str(valor_esperado),
            })

        # Aplicar la corrección
        df_corregido.loc[mascara_distinto, columna] = valor_esperado

        resumen_por_columna[columna] = {
            "valor_esperado": str(valor_esperado),
            "filas_corregidas": len(filas_afectadas),
            "ejemplos": [
                {
                    "fila_excel": _fila_excel(i),
                    "valor_original": str(serie.iloc[i]),
                }
                for i in filas_afectadas[:20]
            ]
        }

    reporte = {
        "nombre": "Auto-corrección de Valores Fijos",
        "total_correcciones": len(correcciones),
        "columnas_corregidas": list(resumen_por_columna.keys()),
        "resumen_por_columna": resumen_por_columna,
        "correcciones": correcciones,
        "hubo_correcciones": len(correcciones) > 0,
    }

    return df_corregido, reporte
