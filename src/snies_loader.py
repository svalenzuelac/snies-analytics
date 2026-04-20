"""
snies_loader.py - Cargador de datos SNIES (flexible)
Acepta cualquier formato de columnas
"""

import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SNIESLoader:
    """Cargador flexible de archivos SNIES"""
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
    
    # Mapeo de columnas posibles
    COLUMN_MAPPING = {
        # Código de institución
        'código de la institución': 'ies_code',
        'codigo de la institucion': 'ies_code',
        'ies_code': 'ies_code',
        'codigo': 'ies_code',
        'code': 'ies_code',
        
        # Nombre institución
        'institución de educación superior (ies)': 'ies_name',
        'institucion de educacion superior (ies)': 'ies_name',
        'ies_name': 'ies_name',
        'nombre': 'ies_name',
        'name': 'ies_name',
        
        # Año
        'año': 'year',
        'ano': 'year',
        'year': 'year',
        'periodo': 'year',
        
        # Estudiantes
        'total_estudiantes': 'total_estudiantes',
        'total estudiantes': 'total_estudiantes',
        'estudiantes': 'total_estudiantes',
        'estudiantes matriculados': 'total_estudiantes',
        
        # Docentes
        'total_docentes': 'total_docentes',
        'total docentes': 'total_docentes',
        'docentes': 'total_docentes',
        'personal docente': 'total_docentes',
        
        # Sector
        'ies_sector': 'ies_sector',
        'sector': 'ies_sector',
        'caracter': 'ies_sector',
        
        # SUE
        'pertenece_sue': 'pertenece_sue',
        'pertenece sue': 'pertenece_sue',
        'sue': 'pertenece_sue',
        
        # Ratio
        'ratio_estudiante_docente': 'ratio_estudiante_docente',
        'ratio e/d': 'ratio_estudiante_docente',
        'ratio': 'ratio_estudiante_docente',
    }
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizar columnas automáticamente"""
        
        df_normalized = df.copy()
        
        # Paso 1: Limpiar espacios y convertir a minúsculas
        df_normalized.columns = (df_normalized.columns
                                  .str.strip()
                                  .str.lower()
                                  .str.replace(' +', ' ', regex=True))
        
        # Paso 2: Mapear columnas conocidas
        rename_dict = {}
        for col in df_normalized.columns:
            if col in self.COLUMN_MAPPING:
                rename_dict[col] = self.COLUMN_MAPPING[col]
        
        if rename_dict:
            logger.info(f"   Renombrando columnas: {rename_dict}")
            df_normalized.rename(columns=rename_dict, inplace=True)
        
        return df_normalized
    
    def load_all(self) -> pd.DataFrame:
        """Cargar todos los archivos SNIES"""
        
        csv_files = list(self.data_dir.glob("*.csv"))
        logger.info(f"📁 Encontrados {len(csv_files)} archivos SNIES")
        
        if not csv_files:
            raise FileNotFoundError(f"No se encontraron CSV en {self.data_dir}")
        
        dfs = []
        
        for file in csv_files:
            logger.info(f"📥 Leyendo: {file.name}")
            
            try:
                # Intentar leer con diferentes encodings
                for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
                    try:
                        df = pd.read_csv(file, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                logger.info(f"   Columnas encontradas: {df.columns.tolist()}")
                
                # Normalizar columnas
                df = self._normalize_columns(df)
                
                logger.info(f"   Columnas después de mapeo: {df.columns.tolist()}")
                logger.info(f"   Registros: {len(df)} ✅")
                
                dfs.append(df)
                
            except Exception as e:
                logger.error(f"   ❌ Error: {e}")
                continue
        
        if not dfs:
            raise ValueError("No se pudieron cargar archivos SNIES")
        
        df_combined = pd.concat(dfs, ignore_index=True)
        logger.info(f"📊 Total registros: {len(df_combined)}")
        
        return df_combined
    
    def validate_structure(self, df: pd.DataFrame) -> bool:
        """Validar estructura"""
        
        logger.info("🔍 Validando estructura...")
        
        # Columnas obligatorias
        required = ['ies_code', 'ies_name', 'year', 'total_estudiantes', 'total_docentes']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            logger.warning(f"⚠️  Columnas faltantes: {missing}")
            logger.info(f"   Columnas disponibles: {df.columns.tolist()}")
            return False
        
        logger.info("✅ Validación OK")
        return True
