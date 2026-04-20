"""
db_loader.py - Cargar datos transformados en PostgreSQL
"""

import pandas as pd
import logging
from sqlalchemy import create_engine, inspect, text
from typing import Optional
import time

logger = logging.getLogger(__name__)

class PostgreSQLLoader:
    """Cargador de datos a PostgreSQL con control de calidad"""
    
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string, echo=False)
        self.conn = None
        logger.info(f"🔗 Conexión PostgreSQL inicializada")
    
    def create_schema(self, schema_sql: str) -> bool:
        """Ejecutar DDL para crear tablas"""
        
        logger.info("📋 Creando esquema...")
        
        try:
            with self.engine.connect() as conn:
                # Dividir por punto y coma y ejecutar cada statement
                statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                
                for stmt in statements:
                    conn.execute(text(stmt))
                    logger.info(f"  ✅ Ejecutado: {stmt[:60]}...")
                
                conn.commit()
            
            logger.info("✅ Esquema creado exitosamente")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error creando esquema: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """Verificar si tabla existe"""
        inspector = inspect(self.engine)
        return table_name in inspector.get_table_names()
    
    def insert_data(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append') -> int:
        """
        Insertar datos en tabla
        
        Args:
            df: DataFrame con datos
            table_name: Nombre de tabla destino
            if_exists: 'fail', 'replace', 'append'
        
        Returns:
            Número de filas insertadas
        """
        
        logger.info(f"📥 Insertando {len(df)} registros en {table_name}...")
        
        try:
            start_time = time.time()
            
            # Validar tipos antes de insertar
            df_clean = self._validate_types(df)
            
            # Insertar
            df_clean.to_sql(
                table_name,
                self.engine,
                if_exists=if_exists,
                index=False,
                chunksize=1000,
                method='multi'  # Más rápido que predeterminado
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ {len(df)} registros insertados en {elapsed:.2f}s")
            
            return len(df)
        
        except Exception as e:
            logger.error(f"❌ Error insertando datos: {e}")
            raise
    
    @staticmethod
    def _validate_types(df: pd.DataFrame) -> pd.DataFrame:
        """Validar y convertir tipos de datos"""
        
        df_clean = df.copy()
        
        # Numeric columns
        numeric_cols = ['CÓDIGO DE LA INSTITUCIÓN', 'AÑO', 'TOTAL_ESTUDIANTES', 
                       'TOTAL_DOCENTES', 'RATIO_ESTUDIANTE_DOCENTE']
        
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # String columns
        string_cols = ['INSTITUCIÓN DE EDUCACIÓN SUPERIOR (IES)', 'SECTOR IES', 'PERTENECE_SUE']
        
        for col in string_cols:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()
        
        return df_clean
    
    def run_data_quality_checks(self, table_name: str) -> dict:
        """Ejecutar checks de calidad post-load"""
        
        logger.info(f"✅ Ejecutando validaciones de calidad en {table_name}...")
        
        checks = {}
        
        try:
            with self.engine.connect() as conn:
                # Total de registros
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                checks['total_records'] = result.scalar()
                
                # Nulos por columna
                result = conn.execute(text(f"""
                    SELECT 
                        'TOTAL_ESTUDIANTES' as column_name,
                        COUNT(*) - COUNT(TOTAL_ESTUDIANTES) as null_count
                    FROM {table_name}
                """))
                null_students = result.scalar()
                checks['null_students'] = null_students
                
                # Rango de E/D
                result = conn.execute(text(f"""
                    SELECT 
                        MIN(RATIO_ESTUDIANTE_DOCENTE),
                        MAX(RATIO_ESTUDIANTE_DOCENTE),
                        AVG(RATIO_ESTUDIANTE_DOCENTE)
                    FROM {table_name}
                """))
                row = result.fetchone()
                checks['ratio_min'] = float(row[0]) if row[0] else None
                checks['ratio_max'] = float(row[1]) if row[1] else None
                checks['ratio_avg'] = float(row[2]) if row[2] else None
                
                # Distribución SUE
                result = conn.execute(text(f"""
                    SELECT PERTENECE_SUE, COUNT(*) 
                    FROM {table_name} 
                    GROUP BY PERTENECE_SUE
                """))
                checks['sue_distribution'] = {row[0]: row[1] for row in result.fetchall()}
        
        except Exception as e:
            logger.error(f"Error en validaciones: {e}")
            checks['error'] = str(e)
        
        return checks
    
    def print_quality_report(self, checks: dict):
        """Mostrar reporte de calidad"""
        
        print("\n" + "="*70)
        print("REPORTE DE CALIDAD POST-CARGA")
        print("="*70)
        
        if 'error' in checks:
            print(f"\n❌ Error: {checks['error']}")
            return
        
        print(f"\n📊 Total de registros: {checks.get('total_records', 'N/A')}")
        print(f"Nulos en ESTUDIANTES: {checks.get('null_students', 0)}")
        
        if 'ratio_avg' in checks:
            print(f"\n📈 Métrica E/D:")
            print(f"  Mínimo: {checks['ratio_min']:.2f}")
            print(f"  Máximo: {checks['ratio_max']:.2f}")
            print(f"  Promedio: {checks['ratio_avg']:.2f}")
        
        if 'sue_distribution' in checks:
            print(f"\n🏛️  Distribución SUE:")
            for sue_status, count in checks['sue_distribution'].items():
                print(f"  {sue_status}: {count} registros")
        
        print("\n" + "="*70)
    
    def close(self):
        """Cerrar conexión"""
        if self.engine:
            self.engine.dispose()
            logger.info("🔌 Conexión cerrada")


if __name__ == "__main__":
    # Ejemplo de uso
    import sys
    sys.path.insert(0, '/home/claude')
    from src_snies_loader import SNIESLoader
    from src_transformation import SNIESTransformer
    from src_config import DATABASE_URL, SUE_INSTITUTIONS
    from pathlib import Path
    
    # Cargar datos
    loader = SNIESLoader(Path("/home/claude/data_extracted"))
    df_raw = loader.load_all()
    
    # Transformar
    df_transformed = (
        SNIESTransformer(df_raw)
        .clean()
        .normalize_ies_names()
        .enrich_with_teachers()
        .add_sue_classification(SUE_INSTITUTIONS)
        .validate_ranges()
        .get_result()
    )
    
    # Cargar a DB
    db_loader = PostgreSQLLoader(DATABASE_URL)
    
    # Mostrar primeras filas
    print("\nMuestra de datos a cargar:")
    print(df_transformed.head(10).to_string())
