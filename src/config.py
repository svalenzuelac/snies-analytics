"""
config.py - Configuración centralizada del proyecto SNIES
Maneja: variables de entorno, conexiones a DB, paths
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# RUTAS
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Crear directorios si no existen
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# VARIABLES DE ENTORNO
def get_env(key: str, default: Optional[str] = None) -> str:
    """Obtener variable de entorno con fallback seguro"""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Variable de entorno requerida no encontrada: {key}")
    return value

# DATABASE
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "snies_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# LOGGING
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# AÑOS DISPONIBLES
ANALYSIS_YEARS = [2022, 2023, 2024]

# VALIDACIONES
MIN_STUDENTS = 0
MAX_STUDENTS = 100000
MIN_TEACHERS = 0
MAX_TEACHERS = 10000

# SUE (Sistema Universitario Estatal) - IES públicas reconocidas
SUE_INSTITUTIONS = {
    '1101': 'UNIVERSIDAD NACIONAL DE COLOMBIA',
    '1105': 'UNIVERSIDAD PEDAGOGICA NACIONAL',
    '1117': 'UNIVERSIDAD MILITAR-NUEVA GRANADA',
    '1301': 'UNIVERSIDAD DISTRITAL-FRANCISCO JOSE DE CALDAS',
    '1121': 'UNIVERSIDAD-COLEGIO MAYOR DE CUNDINAMARCA',
}

logger.info(f"Configuración cargada: {DB_NAME} en {DB_HOST}:{DB_PORT}")
