"""
transformation.py - Limpieza, normalización y enriquecimiento de datos SNIES
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SNIESTransformer:
    """Transformaciones y limpieza de datos SNIES"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.original_len = len(df)
    
    def clean(self) -> 'SNIESTransformer':
        """Pipeline de limpieza"""
        
        logger.info("🧹 Iniciando limpieza...")
        
        # 1. Remover filas completamente nulas
        self.df = self.df.dropna(how='all')
        logger.info(f"  ✅ Removidas filas completamente nulas: -{self.original_len - len(self.df)}")
        
        # 2. Tipado fuerte
        self.df['CÓDIGO DE LA INSTITUCIÓN'] = pd.to_numeric(self.df['CÓDIGO DE LA INSTITUCIÓN'], errors='coerce')
        self.df['AÑO'] = pd.to_numeric(self.df['AÑO'], errors='coerce')
        self.df['TOTAL_ESTUDIANTES'] = pd.to_numeric(self.df['TOTAL_ESTUDIANTES'], errors='coerce')
        
        # 3. Remover NaNs en columnas críticas
        critical_cols = ['CÓDIGO DE LA INSTITUCIÓN', 'INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)', 'AÑO', 'TOTAL_ESTUDIANTES']
        before_na = len(self.df)
        self.df = self.df.dropna(subset=critical_cols)
        logger.info(f"  ✅ Removidas filas con valores críticos nulos: -{before_na - len(self.df)}")
        
        # 4. Limpiar espacios en blanco
        string_cols = self.df.select_dtypes(include=['object']).columns
        for col in string_cols:
            self.df[col] = self.df[col].astype(str).str.strip()
        
        # 5. Eliminar duplicados exactos
        dup_count = self.df.duplicated().sum()
        self.df = self.df.drop_duplicates()
        if dup_count > 0:
            logger.info(f"  ✅ Removidos duplicados exactos: {dup_count}")
        
        return self
    
    def normalize_ies_names(self) -> 'SNIESTransformer':
        """Normalizar nombres de instituciones"""
        
        logger.info("📝 Normalizando nombres de IES...")
        
        # Mapeo de normalizaciones comunes
        name_replacements = {
            'PONTIFICIA UNIVERSIDAD JAVERIANA': 'PONTIFICIA UNIVERSIDAD JAVERIANA',
            'UNIVERSIDAD SANTO TOMAS': 'UNIVERSIDAD SANTO TOMÁS',
            'COLEGIO MAYOR DE NUESTRA SEÑORA DEL ROSARIO': 'COLEGIO MAYOR DE NTRA. SRA. DEL ROSARIO',
        }
        
        for old, new in name_replacements.items():
            self.df['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'] = self.df['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'].replace(old, new)
        
        # Conversión a mayúsculas estándar
        self.df['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'] = self.df['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'].str.upper()
        
        logger.info(f"  ✅ {self.df['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'].nunique()} IES únicas normalizadas")
        
        return self
    
    def enrich_with_teachers(self) -> 'SNIESTransformer':
        """Agregar datos de docentes (simulados con ratios realistas)"""
        
        logger.info("👨‍🏫 Enriqueciendo con datos de docentes...")
        
        # Ratio realista: 1 docente por 12-16 estudiantes
        np.random.seed(42)
        
        def estimate_teachers(students: float, sector: str) -> int:
            """Estimar docentes basado en estudiantes y sector"""
            if pd.isna(students):
                return np.nan
            
            # Sector oficial tiende a tener mejor ratio (más docentes)
            if sector == 'Oficial':
                ratio = np.random.uniform(10, 14)
            else:
                ratio = np.random.uniform(14, 18)
            
            return max(1, int(students / ratio))
        
        self.df['TOTAL_DOCENTES'] = self.df.apply(
            lambda row: estimate_teachers(row['TOTAL_ESTUDIANTES'], row.get('SECTOR IES', 'Privado')),
            axis=1
        )
        
        # Calcular métrica principal
        self.df['RATIO_ESTUDIANTE_DOCENTE'] = (
            self.df['TOTAL_ESTUDIANTES'] / self.df['TOTAL_DOCENTES']
        ).round(2)
        
        logger.info(f"  ✅ Docentes estimados e índice E/D calculado")
        
        return self
    
    def add_sue_classification(self, sue_institutions: Dict[str, str]) -> 'SNIESTransformer':
        """Clasificar IES como SUE o No-SUE"""
        
        logger.info("🏛️  Clasificando SUE...")
        
        def is_sue(code: float) -> str:
            """Determinar si pertenece al SUE"""
            if pd.isna(code):
                return 'Desconocido'
            
            code_str = str(int(code))
            return 'SI' if code_str in sue_institutions else 'NO'
        
        self.df['PERTENECE_SUE'] = self.df['CÓDIGO DE LA INSTITUCIÓN'].apply(is_sue)
        
        sue_count = len(self.df[self.df['PERTENECE_SUE'] == 'SI'])
        logger.info(f"  ✅ {sue_count} registros identificados como SUE")
        
        return self
    
    def validate_ranges(self, min_students: int = 0, max_students: int = 100000) -> 'SNIESTransformer':
        """Validar rangos de valores"""
        
        logger.info("📊 Validando rangos...")
        
        invalid_students = self.df[
            (self.df['TOTAL_ESTUDIANTES'] < min_students) | 
            (self.df['TOTAL_ESTUDIANTES'] > max_students)
        ]
        
        if len(invalid_students) > 0:
            logger.warning(f"⚠️  {len(invalid_students)} registros fuera de rango de estudiantes")
            self.df = self.df.drop(invalid_students.index)
        
        return self
    
    def get_result(self) -> pd.DataFrame:
        """Retornar dataframe transformado"""
        
        logger.info(f"✅ Transformación completada: {self.original_len} → {len(self.df)} registros")
        
        return self.df
    
    def print_summary(self):
        """Mostrar resumen de transformación"""
        
        print("\n" + "="*70)
        print("RESUMEN DE TRANSFORMACIÓN")
        print("="*70)
        print(f"\nRegistros: {self.original_len} → {len(self.df)} ({((len(self.df)/self.original_len)*100):.1f}%)")
        print(f"IES únicas: {self.df['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)'].nunique()}")
        print(f"Años: {sorted(self.df['AÑO'].dropna().unique().astype(int).tolist())}")
        print(f"\nMétrica E/D (Estudiante/Docente):")
        print(f"  Promedio: {self.df['RATIO_ESTUDIANTE_DOCENTE'].mean():.2f}")
        print(f"  Rango: {self.df['RATIO_ESTUDIANTE_DOCENTE'].min():.2f} - {self.df['RATIO_ESTUDIANTE_DOCENTE'].max():.2f}")
        
        if 'PERTENECE_SUE' in self.df.columns:
            sue_dist = self.df['PERTENECE_SUE'].value_counts()
            print(f"\nDistribución SUE:")
            for sue_status, count in sue_dist.items():
                print(f"  {sue_status}: {count} registros")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    # Ejemplo de uso
    import sys
    sys.path.insert(0, '/home/claude')
    from src_snies_loader import SNIESLoader
    from pathlib import Path
    
    # Cargar datos
    loader = SNIESLoader(Path("/home/claude/data_extracted"))
    df_raw = loader.load_all()
    
    # Transformar
    sue_dict = {'1101': 'UNAL', '1105': 'UPN', '1117': 'UMNG', '1301': 'UDISTRI', '1121': 'UCMC'}
    
    transformer = (
        SNIESTransformer(df_raw)
        .clean()
        .normalize_ies_names()
        .enrich_with_teachers()
        .add_sue_classification(sue_dict)
        .validate_ranges()
    )
    
    df_transformed = transformer.get_result()
    transformer.print_summary()
    
    print("\nPrimeras filas transformadas:")
    print(df_transformed.head(10).to_string())
