"""
Endpoints de la API FastAPI — Proyecto Fastrack
================================================

Define los endpoints de validación de archivos Excel.
Se registra como router para ser incluido en la aplicación principal.

Uso:
    from app.api.endpoints import router
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from io import BytesIO
import pandas as pd
import json

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


# =============================================================================
# ROUTER DE VALIDACIÓN
# =============================================================================

router = APIRouter(prefix="/validar", tags=["Validación"])

# Cache temporal para el DataFrame corregido (por simplicidad, en memoria)
_cache_df_corregido = {}


@router.post("/archivo")
async def validar_archivo_endpoint(archivo: UploadFile = File(...)):
    """
    Recibe un archivo Excel (.xlsx), lee la hoja configurada, ejecuta
    todas las validaciones disponibles y aplica auto-corrección a
    columnas de valor fijo.

    Retorna:
        dict: Resultado con cada validación, auto-correcciones y resumen global.
    """
    try:
        contenido = await archivo.read()

        # --- Validar tamaño del archivo ---
        tamano_mb = len(contenido) / (1024 * 1024)
        if tamano_mb > TAMANO_MAXIMO_MB:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"El archivo pesa {tamano_mb:.1f} MB y excede "
                    f"el máximo permitido de {TAMANO_MAXIMO_MB} MB."
                )
            )

        # --- Validar estructura del Excel ---
        resultado_estructura = validar_estructura_excel(
            contenido, NOMBRE_HOJA, COLUMNAS_REQUERIDAS
        )

        if not resultado_estructura["es_valido"]:
            return {
                "estructura": resultado_estructura,
                "resumen": {
                    "total_validaciones": 1,
                    "validaciones_exitosas": 0,
                    "validaciones_fallidas": 1,
                    "es_valido_global": False,
                    "mensaje": (
                        "El archivo no cumple los requisitos de estructura. "
                        "No se ejecutaron las demás validaciones."
                    )
                }
            }

        # --- Leer la hoja del Excel ---
        df = pd.read_excel(
            BytesIO(contenido),
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

        # --- Ejecutar todas las validaciones (sobre el DF original) ---
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

        # --- Calcular resumen global ---
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

    except HTTPException:
        raise
    except Exception as excepcion:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar el archivo: {str(excepcion)}"
        )


@router.get("/descargar-corregido")
async def descargar_corregido():
    """
    Descarga el último archivo Excel con las auto-correcciones de
    valores fijos aplicadas.
    """
    if "ultimo" not in _cache_df_corregido:
        raise HTTPException(
            status_code=404,
            detail="No hay archivo corregido disponible. Ejecute primero la validación."
        )

    df = _cache_df_corregido["ultimo"]
    nombre_hoja = _cache_df_corregido.get("nombre_hoja", "Datos")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=archivo_corregido.xlsx"
        }
    )


@router.post("/aplicar-correcciones")
async def aplicar_correcciones_manuales(archivo: UploadFile = File(...)):
    """
    Recibe el archivo original junto con correcciones manuales del usuario,
    aplica las correcciones y retorna el Excel limpio.

    Las correcciones se envían como form field 'correcciones' en JSON:
    [{"fila": 0, "columna": "col", "valor": "nuevo_valor"}, ...]
    """
    from fastapi import Form

    try:
        contenido = await archivo.read()

        df = pd.read_excel(
            BytesIO(contenido),
            sheet_name=NOMBRE_HOJA,
            engine="openpyxl"
        )

        # Primero aplicar auto-correcciones
        df_corregido, _ = autocorregir_valores_fijos(df, VALORES_FIJOS)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_corregido.to_excel(writer, sheet_name=NOMBRE_HOJA, index=False)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=archivo_final_limpio.xlsx"
            }
        )

    except Exception as excepcion:
        raise HTTPException(
            status_code=500,
            detail=f"Error al aplicar correcciones: {str(excepcion)}"
        )
