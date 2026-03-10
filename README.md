# Fastrack — Validador de Precios Residenciales

Sistema de validación automática de archivos Excel de precios residenciales para **Movistar**.

## Estructura del Proyecto

```
Proyecto_Fastrack/
├── app/                          # Paquete principal
│   ├── api/
│   │   └── endpoints.py         # Endpoints FastAPI (validaciones)
│   ├── nucleo/
│   │   └── config.py            # Configuración centralizada
│   ├── servicios/
│   │   └── validaciones.py      # Motor de 8 funciones de validación
│   ├── templates/
│   │   └── index.html           # Frontend Movistar
│   └── servidor.py              # Servidor Flask (BFF)
├── tests/
│   └── test_validaciones.py     # 26 tests unitarios
├── main.py                      # Punto de entrada principal
├── requirements.txt              # Dependencias
└── README.md                     # Este archivo
```

## Instalación

```bash
# Clonar o descargar el proyecto
cd Proyecto_Fastrack

# Instalar dependencias
py -3.12 -m pip install -r requirements.txt
```

## Ejecución (Desarrollo)

El sistema necesita **dos terminales**:

```bash
# Terminal 1 — API de validación (puerto 8000)
py -3.12 -m uvicorn main:api --reload

# Terminal 2 — Frontend web (puerto 5000)
py -3.12 main.py
```

Abrir en el navegador: **http://127.0.0.1:5000**

## Ejecución (Producción)

```bash
# API
py -3.12 -m uvicorn main:api --host 0.0.0.0 --port 8000 --workers 4

# Frontend
py -3.12 -m gunicorn main:flask_app -b 0.0.0.0:5000 --workers 2
```

## Tests

```bash
py -3.12 -m pytest tests/ -v
```

## Validaciones incluidas

| # | Validación | Descripción |
|---|-----------|-------------|
| 1 | Estructura | Verifica hoja y columnas del Excel |
| 2 | Nulos | Detecta valores vacíos en columnas obligatorias |
| 3 | Únicos | Verifica que SEGMENTO, MONEDA, TARIFA_SOCIAL tengan un solo valor |
| 4 | Precios | Valida formato numérico, negativos y rangos |
| 5 | Fechas | Valida formato dd/mm/yyyy |
| 6 | Duplicados | Detecta filas duplicadas por columnas clave |
| 7 | Coherencia de fechas | Verifica que FECHA_FIN > FECHA_EFECTIVA |
| 8 | Escalamiento | Verifica que precios por plazo sean consistentes |
| 9 | Espacios ocultos | Detecta espacios al inicio/final en textos |

## Documentación de la API

Con la API corriendo, acceder a:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
