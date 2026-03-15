"""
Inicialización de Base de Datos — Proyecto Fastrack
=====================================================

Script para crear/reiniciar la base de datos SQLite.
Crea todas las tablas y el usuario admin por defecto.

Uso:
    py -3.12 init_db.py
"""

import os
import sys

# Agregar raíz del proyecto al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.nucleo.config import RUTA_BD
from app.nucleo.database import inicializar_bd, obtener_tablas


def main():
    """Punto de entrada del script de inicialización."""
    print("=" * 60)
    print("  Fastrack — Inicialización de Base de Datos")
    print("=" * 60)
    print()

    print(f"  Archivo BD: {RUTA_BD}")
    ya_existe = os.path.exists(RUTA_BD)
    print(f"  Estado:     {'Existe (se actualizará)' if ya_existe else 'Nueva (se creará)'}")
    print()

    inicializar_bd()

    # Verificar tablas creadas
    tablas = obtener_tablas()
    print()
    print(f"  Tablas en la BD ({len(tablas)}):")
    for tabla in tablas:
        print(f"    [OK] {tabla}")

    print()
    print("=" * 60)
    print("  ¡Listo! La base de datos está configurada.")
    print("=" * 60)


if __name__ == "__main__":
    main()
