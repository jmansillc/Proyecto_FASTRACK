"""
Tests Unitarios para Validaciones — Proyecto Fastrack
=====================================================

Ejecutar con:
    py -3.12 -m pytest tests/ -v
"""

import sys
import os
import pytest
import pandas as pd

# Agregar raíz del proyecto al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.servicios.validaciones import (
    validar_nulos,
    validar_unicos,
    validar_precio,
    validar_fecha,
    validar_duplicados,
    validar_coherencia_fechas,
    validar_escalamiento_precios,
    validar_espacios_en_blanco,
    validar_longitud,
    validar_valores_permitidos,
)
from app.servicios.correcciones import autocorregir_valores_fijos


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def df_correcto():
    """DataFrame con datos completamente válidos."""
    return pd.DataFrame({
        "Modelo": ["A", "B", "C"],
        "FORMA DE PAGO": ["Contado", "Crédito", "Contado"],
        "TRANSACCION": ["Alta", "Baja", "Cambio"],
        "GRUPO_PLAN": ["Plan1", "Plan2", "Plan3"],
        "SEGMENTO": ["R", "R", "R"],
        "MONEDA": ["PEN", "PEN", "PEN"],
        "TARIFA_SOCIAL": ["NO", "NO", "NO"],
        "SUBTIPO_CLIENTE": ["CNA", "CNA", "CNA"],
        "GRUPO_VALOR_SUBSCRIPCION": ["POS1", "POS1", "POS1"],
        "PRECIO_0M": [100, 200, 300],
        "PRECIO_6M": [150, 250, 350],
        "PRECIO_12M": [200, 300, 400],
        "PRECIO_18M": [250, 350, 450],
        "PRECIO_24M": [300, 400, 500],
        "PRECIO_36M": [350, 450, 550],
        "FECHA_EFECTIVA": ["01/01/2026", "01/02/2026", "01/03/2026"],
        "FECHA_FIN": ["31/12/2026", "31/12/2026", "31/12/2026"],
    })


@pytest.fixture
def df_con_nulos():
    """DataFrame con valores nulos."""
    return pd.DataFrame({
        "Modelo": ["A", None, "C"],
        "MONEDA": ["PEN", "PEN", None],
    })


@pytest.fixture
def df_con_precios_negativos():
    """DataFrame con precios negativos y no numéricos."""
    return pd.DataFrame({
        "PRECIO_0M": [100, -50, "abc"],
        "PRECIO_6M": [200, 300, 400],
    })


# =============================================================================
# TESTS — validar_nulos
# =============================================================================

class TestValidarNulos:
    def test_sin_nulos_es_valido(self, df_correcto):
        resultado = validar_nulos(df_correcto, ["Modelo", "MONEDA"])
        assert resultado["es_valido"] is True

    def test_con_nulos_detecta_errores(self, df_con_nulos):
        resultado = validar_nulos(df_con_nulos, ["Modelo", "MONEDA"])
        assert resultado["es_valido"] is False
        assert "Modelo" in resultado["errores"]

    def test_columna_inexistente(self, df_correcto):
        resultado = validar_nulos(df_correcto, ["COLUMNA_FALSA"])
        assert resultado["es_valido"] is False

    def test_nombre_validacion(self, df_correcto):
        resultado = validar_nulos(df_correcto, ["Modelo"])
        assert "nombre_validacion" in resultado

    def test_nulos_retorna_filas_excel(self, df_con_nulos):
        resultado = validar_nulos(df_con_nulos, ["Modelo"])
        filas = resultado["errores"]["Modelo"]["filas_excel"]
        assert len(filas) == 1
        assert filas[0]["fila_excel"] == 3


# =============================================================================
# TESTS — validar_unicos
# =============================================================================

class TestValidarUnicos:
    def test_valor_unico_es_valido(self, df_correcto):
        resultado = validar_unicos(df_correcto, ["SEGMENTO"])
        assert resultado["es_valido"] is True

    def test_multiples_valores_falla(self, df_correcto):
        resultado = validar_unicos(df_correcto, ["Modelo"])
        assert resultado["es_valido"] is False

    def test_columna_inexistente(self, df_correcto):
        resultado = validar_unicos(df_correcto, ["NO_EXISTE"])
        assert resultado["es_valido"] is False


# =============================================================================
# TESTS — validar_precio
# =============================================================================

class TestValidarPrecio:
    def test_precios_validos(self, df_correcto):
        resultado = validar_precio(df_correcto, ["PRECIO_0M", "PRECIO_6M"])
        assert resultado["es_valido"] is True

    def test_precios_negativos(self, df_con_precios_negativos):
        resultado = validar_precio(df_con_precios_negativos, ["PRECIO_0M"])
        assert resultado["es_valido"] is False

    def test_precios_no_numericos(self, df_con_precios_negativos):
        resultado = validar_precio(df_con_precios_negativos, ["PRECIO_0M"])
        assert resultado["es_valido"] is False

    def test_precios_fuera_de_rango(self):
        df = pd.DataFrame({"PRECIO": [100, 2000000]})
        resultado = validar_precio(df, ["PRECIO"], 0, 999999)
        assert resultado["es_valido"] is False

    def test_columna_inexistente(self, df_correcto):
        resultado = validar_precio(df_correcto, ["PRECIO_FALSO"])
        assert resultado["es_valido"] is False

    def test_precio_retorna_filas_excel(self, df_con_precios_negativos):
        resultado = validar_precio(df_con_precios_negativos, ["PRECIO_0M"])
        detalle = resultado["errores"]["PRECIO_0M"]["detalle"]
        for tipo, sub in detalle.items():
            assert "filas_excel" in sub


# =============================================================================
# TESTS — validar_fecha
# =============================================================================

class TestValidarFecha:
    def test_fechas_validas(self, df_correcto):
        resultado = validar_fecha(df_correcto, ["FECHA_EFECTIVA"])
        assert resultado["es_valido"] is True

    def test_fechas_invalidas(self):
        df = pd.DataFrame({"FECHA": ["2026-01-01", "no_fecha", "01/01/2026"]})
        resultado = validar_fecha(df, ["FECHA"])
        assert resultado["es_valido"] is False

    def test_columna_inexistente(self, df_correcto):
        resultado = validar_fecha(df_correcto, ["FECHA_FALSA"])
        assert resultado["es_valido"] is False

    def test_fecha_retorna_filas_excel(self):
        df = pd.DataFrame({"FECHA": ["no_fecha", "01/01/2026"]})
        resultado = validar_fecha(df, ["FECHA"])
        filas = resultado["errores"]["FECHA"]["filas_excel"]
        assert filas[0]["fila_excel"] == 2


# =============================================================================
# TESTS — validar_duplicados
# =============================================================================

class TestValidarDuplicados:
    def test_sin_duplicados(self, df_correcto):
        resultado = validar_duplicados(df_correcto, ["Modelo"])
        assert resultado["es_valido"] is True

    def test_con_duplicados(self):
        df = pd.DataFrame({"Modelo": ["A", "A", "B"], "PLAN": ["X", "X", "Y"]})
        resultado = validar_duplicados(df, ["Modelo", "PLAN"])
        assert resultado["es_valido"] is False

    def test_columna_clave_inexistente(self, df_correcto):
        resultado = validar_duplicados(df_correcto, ["NO_EXISTE"])
        assert resultado["es_valido"] is False

    def test_duplicados_retorna_filas_excel(self):
        df = pd.DataFrame({"Modelo": ["A", "A", "B"]})
        resultado = validar_duplicados(df, ["Modelo"])
        assert resultado["filas_excel_duplicadas"][0] == 2


# =============================================================================
# TESTS — validar_coherencia_fechas
# =============================================================================

class TestValidarCoherenciaFechas:
    def test_fechas_coherentes(self, df_correcto):
        resultado = validar_coherencia_fechas(df_correcto)
        assert resultado["es_valido"] is True

    def test_fechas_invertidas(self):
        df = pd.DataFrame({
            "FECHA_EFECTIVA": ["31/12/2026"],
            "FECHA_FIN": ["01/01/2026"],
        })
        resultado = validar_coherencia_fechas(df)
        assert resultado["es_valido"] is False

    def test_columna_faltante(self):
        df = pd.DataFrame({"OTRA": [1]})
        resultado = validar_coherencia_fechas(df)
        assert resultado["es_valido"] is False

    def test_coherencia_retorna_filas_excel(self):
        df = pd.DataFrame({
            "FECHA_EFECTIVA": ["31/12/2026"],
            "FECHA_FIN": ["01/01/2026"],
        })
        resultado = validar_coherencia_fechas(df)
        assert resultado["filas_excel"][0]["fila_excel"] == 2


# =============================================================================
# TESTS — validar_escalamiento_precios
# =============================================================================

class TestValidarEscalamientoPrecios:
    def test_escalamiento_correcto(self, df_correcto):
        cols = ["PRECIO_0M", "PRECIO_6M", "PRECIO_12M",
                "PRECIO_18M", "PRECIO_24M", "PRECIO_36M"]
        resultado = validar_escalamiento_precios(df_correcto, cols)
        assert resultado["es_valido"] is True

    def test_escalamiento_inconsistente(self):
        df = pd.DataFrame({
            "PRECIO_0M": [100], "PRECIO_6M": [50],
            "PRECIO_12M": [200], "PRECIO_18M": [250],
            "PRECIO_24M": [300], "PRECIO_36M": [350],
        })
        cols = ["PRECIO_0M", "PRECIO_6M", "PRECIO_12M",
                "PRECIO_18M", "PRECIO_24M", "PRECIO_36M"]
        resultado = validar_escalamiento_precios(df, cols)
        assert resultado["es_valido"] is False

    def test_escalamiento_retorna_fila_excel(self):
        df = pd.DataFrame({
            "PRECIO_0M": [100], "PRECIO_6M": [50],
            "PRECIO_12M": [200], "PRECIO_18M": [250],
            "PRECIO_24M": [300], "PRECIO_36M": [350],
        })
        cols = ["PRECIO_0M", "PRECIO_6M", "PRECIO_12M",
                "PRECIO_18M", "PRECIO_24M", "PRECIO_36M"]
        resultado = validar_escalamiento_precios(df, cols)
        assert resultado["inconsistencias"][0]["fila_excel"] == 2


# =============================================================================
# TESTS — validar_espacios_en_blanco
# =============================================================================

class TestValidarEspaciosEnBlanco:
    def test_sin_espacios(self, df_correcto):
        resultado = validar_espacios_en_blanco(df_correcto, ["Modelo"])
        assert resultado["es_valido"] is True

    def test_con_espacios(self):
        df = pd.DataFrame({"Modelo": [" A", "B ", " C "]})
        resultado = validar_espacios_en_blanco(df, ["Modelo"])
        assert resultado["es_valido"] is False

    def test_columna_inexistente(self, df_correcto):
        resultado = validar_espacios_en_blanco(df_correcto, ["NO_EXISTE"])
        assert resultado["es_valido"] is False

    def test_espacios_retorna_filas_excel(self):
        df = pd.DataFrame({"Modelo": [" A", "B"]})
        resultado = validar_espacios_en_blanco(df, ["Modelo"])
        assert resultado["errores"]["Modelo"]["filas_excel"][0]["fila_excel"] == 2


# =============================================================================
# TESTS — validar_longitud
# =============================================================================

class TestValidarLongitud:
    def test_longitud_correcta(self):
        df = pd.DataFrame({"Modelo": ["ABC", "DEFG"]})
        resultado = validar_longitud(df, {"Modelo": 10})
        assert resultado["es_valido"] is True

    def test_longitud_excedida(self):
        df = pd.DataFrame({"Modelo": ["Texto muy largo que excede", "OK"]})
        resultado = validar_longitud(df, {"Modelo": 5})
        assert resultado["es_valido"] is False

    def test_longitud_retorna_filas_excel(self):
        df = pd.DataFrame({"Modelo": ["ExcedeMaximo", "OK"]})
        resultado = validar_longitud(df, {"Modelo": 5})
        filas = resultado["errores"]["Modelo"]["filas_excel"]
        assert filas[0]["fila_excel"] == 2
        assert filas[0]["longitud"] == 12

    def test_nombre_validacion(self):
        df = pd.DataFrame({"A": ["x"]})
        resultado = validar_longitud(df, {"A": 10})
        assert resultado["nombre_validacion"] == "Longitud de Texto"

    def test_columna_inexistente_no_falla(self):
        df = pd.DataFrame({"A": ["x"]})
        resultado = validar_longitud(df, {"NO_EXISTE": 10})
        assert resultado["es_valido"] is True


# =============================================================================
# TESTS — validar_valores_permitidos
# =============================================================================

class TestValidarValoresPermitidos:
    def test_valores_validos(self):
        df = pd.DataFrame({"SUBTIPO_CLIENTE": ["CNA", "NA", "CNA"]})
        resultado = validar_valores_permitidos(df, {"SUBTIPO_CLIENTE": ["CNA", "NA"]})
        assert resultado["es_valido"] is True

    def test_valor_no_permitido(self):
        df = pd.DataFrame({"SUBTIPO_CLIENTE": ["CNA", "INVALIDO", "NA"]})
        resultado = validar_valores_permitidos(df, {"SUBTIPO_CLIENTE": ["CNA", "NA"]})
        assert resultado["es_valido"] is False
        assert resultado["errores"]["SUBTIPO_CLIENTE"]["cantidad"] == 1

    def test_retorna_filas_excel(self):
        df = pd.DataFrame({"FORMA DE PAGO": ["TELEF001", "MALO", "TELEF002"]})
        resultado = validar_valores_permitidos(df, {"FORMA DE PAGO": ["TELEF001", "TELEF002"]})
        filas = resultado["errores"]["FORMA DE PAGO"]["filas_excel"]
        assert filas[0]["fila_excel"] == 3
        assert filas[0]["valor"] == "MALO"

    def test_columna_inexistente_no_falla(self):
        df = pd.DataFrame({"A": ["x"]})
        resultado = validar_valores_permitidos(df, {"NO_EXISTE": ["X"]})
        assert resultado["es_valido"] is True

    def test_nombre_validacion(self):
        df = pd.DataFrame({"A": ["x"]})
        resultado = validar_valores_permitidos(df, {"A": ["x"]})
        assert resultado["nombre_validacion"] == "Valores Permitidos"


# =============================================================================
# TESTS — autocorregir_valores_fijos
# =============================================================================

class TestAutocorregirValoresFijos:
    def test_sin_correcciones_necesarias(self, df_correcto):
        valores = {"SEGMENTO": "R", "MONEDA": "PEN"}
        df_corregido, reporte = autocorregir_valores_fijos(df_correcto, valores)
        assert reporte["hubo_correcciones"] is False

    def test_corrige_valores_incorrectos(self):
        df = pd.DataFrame({
            "MONEDA": ["PEN", "COP", "USD"],
            "SEGMENTO": ["R", "R", "X"],
        })
        valores = {"MONEDA": "PEN", "SEGMENTO": "R"}
        df_corregido, reporte = autocorregir_valores_fijos(df, valores)
        assert reporte["total_correcciones"] == 3
        assert df_corregido["MONEDA"].tolist() == ["PEN", "PEN", "PEN"]

    def test_no_modifica_df_original(self):
        df = pd.DataFrame({"MONEDA": ["COP"]})
        valores = {"MONEDA": "PEN"}
        df_corregido, _ = autocorregir_valores_fijos(df, valores)
        assert df["MONEDA"].iloc[0] == "COP"
        assert df_corregido["MONEDA"].iloc[0] == "PEN"

    def test_reporte_contiene_detalle(self):
        df = pd.DataFrame({"MONEDA": ["COP", "PEN"]})
        valores = {"MONEDA": "PEN"}
        _, reporte = autocorregir_valores_fijos(df, valores)
        assert "MONEDA" in reporte["columnas_corregidas"]

    def test_columna_inexistente_no_falla(self):
        df = pd.DataFrame({"A": [1]})
        valores = {"NO_EXISTE": "X"}
        _, reporte = autocorregir_valores_fijos(df, valores)
        assert reporte["hubo_correcciones"] is False

    def test_correcciones_tienen_fila_excel(self):
        df = pd.DataFrame({"MONEDA": ["COP", "PEN", "USD"]})
        valores = {"MONEDA": "PEN"}
        _, reporte = autocorregir_valores_fijos(df, valores)
        correcciones = reporte["correcciones"]
        assert correcciones[0]["fila_excel"] == 2
        assert correcciones[0]["valor_original"] == "COP"
