"""
etl_loader.py
ETL para SNIES Analytics - Medallion Architecture
Flujo: CSV (raw) -> Bronze -> Silver -> Gold

Uso:
    python etl_loader.py --csv data/raw/snies_relacion_estudiante_docente.csv --db postgresql://...
"""

import subprocess
import sys

print("=" * 70)
print("📦 Instalando dependencias...")
print("=" * 70)

subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", 
                       "psycopg2-binary", "pandas", "sqlalchemy"])

print("✅ Dependencias instaladas\n")

import psycopg2
from psycopg2.extras import execute_batch
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SNIESETLLoader:
    """ETL Loader para SNIES Analytics"""
    
    def __init__(self, db_connection_string):
        """
        Args:
            db_connection_string: "postgresql://user:password@host:port/database"
        """
        self.conn_string = db_connection_string
        self.conn = None
        self.stats = {
            "bronze_loaded": 0,
            "silver_ies_loaded": 0,
            "silver_est_loaded": 0,
            "silver_doc_loaded": 0,
            "gold_loaded": 0,
            "errors": []
        }
    
    def connect(self):
        """Conectar a PostgreSQL"""
        try:
            self.conn = psycopg2.connect(self.conn_string)
            logger.info("✅ Conectado a PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            raise
    
    def disconnect(self):
        """Desconectar de PostgreSQL"""
        if self.conn:
            self.conn.close()
            logger.info("✅ Conexión cerrada")
    
    def log_audit(self, stage, status, message, records_affected):
        """Registrar en tabla de auditoría"""
        try:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO audit.pipeline_log 
                (stage, status, message, records_affected, started_at, completed_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (stage, status, message, records_affected))
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.warning(f"⚠️  No se pudo registrar auditoría: {e}")
    
    def load_bronze(self, csv_file):
        """PHASE 1: Cargar CSV a tabla bronze.snies_raw"""
        logger.info("\n" + "="*70)
        logger.info("FASE 1: CARGANDO BRONZE (RAW)")
        logger.info("="*70)
        
        try:
            # Leer CSV
            df = pd.read_csv(csv_file, dtype=str)
            logger.info(f"   📥 CSV leído: {len(df)} registros")
            
            # Limpiar valores NaN
            df = df.fillna('')
            
            # Preparar datos para INSERT
            records = []
            for idx, row in df.iterrows():
                try:
                    estudiantes = int(row['total_estudiantes']) if row['total_estudiantes'] else None
                    docentes = int(row['total_docentes']) if row['total_docentes'] else None
                    ratio = float(row['estudiantes_por_docente']) if row['estudiantes_por_docente'] else None
                    
                    records.append((
                        row['ies_name'],
                        int(row['year']),
                        estudiantes,
                        docentes,
                        ratio,
                        row['sector_ies'],
                        row['clasificacion_sue'],
                        Path(csv_file).name
                    ))
                except Exception as e:
                    logger.warning(f"   ⚠️  Error en fila {idx}: {e}")
                    self.stats["errors"].append(f"Row {idx}: {e}")
            
            # Insertar en bronze
            cur = self.conn.cursor()
            cur.execute("TRUNCATE TABLE bronze.snies_raw")
            
            execute_batch(cur, """
                INSERT INTO bronze.snies_raw 
                (ies_name, year, total_estudiantes, total_docentes, 
                 estudiantes_por_docente, sector_ies, clasificacion_sue, source_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, records, page_size=1000)
            
            self.conn.commit()
            self.stats["bronze_loaded"] = len(records)
            
            logger.info(f"   ✅ {len(records)} registros cargados en bronze")
            self.log_audit("bronze", "success", f"Loaded {len(records)} records", len(records))
            
            cur.close()
        
        except Exception as e:
            logger.error(f"   ❌ Error cargando bronze: {e}")
            self.stats["errors"].append(f"Bronze: {e}")
            self.log_audit("bronze", "error", str(e), 0)
            raise
    
    def load_silver(self):
        """PHASE 2: Procesar Bronze -> Silver"""
        logger.info("\n" + "="*70)
        logger.info("FASE 2: CARGANDO SILVER (PROCESSED)")
        logger.info("="*70)
        
        try:
            cur = self.conn.cursor()
            
            # ========== SILVER.SNIES_IES ==========
            logger.info("   📋 Cargando silver.snies_ies...")
            
            cur.execute("TRUNCATE TABLE silver.snies_ies CASCADE")
            
            cur.execute("""
                INSERT INTO silver.snies_ies (ies_name, sector_ies, es_sue)
                SELECT DISTINCT 
                    ies_name,
                    sector_ies,
                    CASE 
                        WHEN clasificacion_sue = 'SUE' THEN TRUE 
                        ELSE FALSE 
                    END
                FROM bronze.snies_raw
                ON CONFLICT (ies_name) DO NOTHING
            """)
            
            count_ies = cur.rowcount
            self.stats["silver_ies_loaded"] = count_ies
            logger.info(f"      ✅ {count_ies} IES cargadas")
            
            # ========== SILVER.SNIES_ESTUDIANTES ==========
            logger.info("   📋 Cargando silver.snies_estudiantes...")
            
            cur.execute("TRUNCATE TABLE silver.snies_estudiantes CASCADE")
            
            cur.execute("""
                INSERT INTO silver.snies_estudiantes (ies_id, year, total_estudiantes)
                SELECT 
                    s.ies_id,
                    b.year,
                    b.total_estudiantes
                FROM bronze.snies_raw b
                JOIN silver.snies_ies s ON b.ies_name = s.ies_name
                WHERE b.total_estudiantes IS NOT NULL
                ON CONFLICT (ies_id, year) DO UPDATE SET total_estudiantes = EXCLUDED.total_estudiantes
            """)
            
            count_est = cur.rowcount
            self.stats["silver_est_loaded"] = count_est
            logger.info(f"      ✅ {count_est} registros de estudiantes cargados")
            
            # ========== SILVER.SNIES_DOCENTES ==========
            logger.info("   📋 Cargando silver.snies_docentes...")
            
            cur.execute("TRUNCATE TABLE silver.snies_docentes CASCADE")
            
            cur.execute("""
                INSERT INTO silver.snies_docentes (ies_id, year, total_docentes)
                SELECT 
                    s.ies_id,
                    b.year,
                    b.total_docentes
                FROM bronze.snies_raw b
                JOIN silver.snies_ies s ON b.ies_name = s.ies_name
                WHERE b.total_docentes IS NOT NULL
                ON CONFLICT (ies_id, year) DO UPDATE SET total_docentes = EXCLUDED.total_docentes
            """)
            
            count_doc = cur.rowcount
            self.stats["silver_doc_loaded"] = count_doc
            logger.info(f"      ✅ {count_doc} registros de docentes cargados")
            
            self.conn.commit()
            logger.info(f"   ✅ SILVER completada")
            self.log_audit("silver", "success", "Silver layer loaded", count_ies + count_est + count_doc)
            
            cur.close()
        
        except Exception as e:
            logger.error(f"   ❌ Error cargando silver: {e}")
            self.stats["errors"].append(f"Silver: {e}")
            self.log_audit("silver", "error", str(e), 0)
            raise
    
    def load_gold(self):
        """PHASE 3: Crear Gold (Star Schema)"""
        logger.info("\n" + "="*70)
        logger.info("FASE 3: CARGANDO GOLD (ANALYTICS)")
        logger.info("="*70)
        
        try:
            cur = self.conn.cursor()
            
            # ========== GOLD.DIM_IES ==========
            logger.info("   📋 Cargando gold.dim_ies...")
            
            cur.execute("TRUNCATE TABLE gold.fact_relacion_estudiante_docente CASCADE")
            cur.execute("TRUNCATE TABLE gold.dim_ies CASCADE")
            
            cur.execute("""
                INSERT INTO gold.dim_ies (ies_id, ies_name, sector_ies, es_sue)
                SELECT ies_id, ies_name, sector_ies, es_sue
                FROM silver.snies_ies
                ON CONFLICT (ies_id) DO UPDATE SET 
                    ies_name = EXCLUDED.ies_name,
                    sector_ies = EXCLUDED.sector_ies,
                    es_sue = EXCLUDED.es_sue
            """)
            
            count_dim_ies = cur.rowcount
            logger.info(f"      ✅ {count_dim_ies} IES en dimensión")
            
            # ========== GOLD.FACT_RELACION ==========
            logger.info("   📋 Cargando gold.fact_relacion_estudiante_docente...")
            
            cur.execute("""
                INSERT INTO gold.fact_relacion_estudiante_docente 
                (dim_ies_id, dim_tiempo_id, total_estudiantes, total_docentes, estudiantes_por_docente)
                SELECT
                    d.dim_ies_id,
                    t.dim_tiempo_id,
                    COALESCE(e.total_estudiantes, 0),
                    COALESCE(do.total_docentes, 0),
                    CASE 
                        WHEN COALESCE(do.total_docentes, 0) > 0 
                        THEN ROUND(COALESCE(e.total_estudiantes, 0)::DECIMAL / do.total_docentes, 2)
                        ELSE NULL
                    END
                FROM gold.dim_ies d
                CROSS JOIN gold.dim_tiempo t
                LEFT JOIN silver.snies_estudiantes e ON d.ies_id = e.ies_id AND t.year = e.year
                LEFT JOIN silver.snies_docentes do ON d.ies_id = do.ies_id AND t.year = do.year
                WHERE d.is_active = TRUE
                ON CONFLICT (dim_ies_id, dim_tiempo_id) DO UPDATE SET
                    total_estudiantes = EXCLUDED.total_estudiantes,
                    total_docentes = EXCLUDED.total_docentes,
                    estudiantes_por_docente = EXCLUDED.estudiantes_por_docente,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            count_fact = cur.rowcount
            self.stats["gold_loaded"] = count_fact
            logger.info(f"      ✅ {count_fact} hechos cargados")
            
            self.conn.commit()
            logger.info(f"   ✅ GOLD completada")
            self.log_audit("gold", "success", "Gold layer loaded", count_fact)
            
            cur.close()
        
        except Exception as e:
            logger.error(f"   ❌ Error cargando gold: {e}")
            self.stats["errors"].append(f"Gold: {e}")
            self.log_audit("gold", "error", str(e), 0)
            raise
    
    def validate_data(self):
        """Validar integridad de datos"""
        logger.info("\n" + "="*70)
        logger.info("VALIDACIÓN DE DATOS")
        logger.info("="*70)
        
        try:
            cur = self.conn.cursor()
            
            # Bronze
            cur.execute("SELECT COUNT(*) FROM bronze.snies_raw")
            bronze_count = cur.fetchone()[0]
            logger.info(f"   bronze.snies_raw: {bronze_count} registros")
            
            # Silver IES
            cur.execute("SELECT COUNT(*) FROM silver.snies_ies")
            ies_count = cur.fetchone()[0]
            logger.info(f"   silver.snies_ies: {ies_count} IES")
            
            # Silver Estudiantes
            cur.execute("SELECT COUNT(*) FROM silver.snies_estudiantes")
            est_count = cur.fetchone()[0]
            logger.info(f"   silver.snies_estudiantes: {est_count} registros")
            
            # Silver Docentes
            cur.execute("SELECT COUNT(*) FROM silver.snies_docentes")
            doc_count = cur.fetchone()[0]
            logger.info(f"   silver.snies_docentes: {doc_count} registros")
            
            # Gold Facts
            cur.execute("SELECT COUNT(*) FROM gold.fact_relacion_estudiante_docente")
            fact_count = cur.fetchone()[0]
            logger.info(f"   gold.fact_relacion_estudiante_docente: {fact_count} hechos")
            
            # Verificar vistas
            logger.info("\n   📊 Verificando vistas...")
            
            cur.execute("SELECT COUNT(*) FROM gold.v_relacion_estudiante_docente")
            view_count = cur.fetchone()[0]
            logger.info(f"   v_relacion_estudiante_docente: {view_count} filas")
            
            cur.execute("SELECT COUNT(*) FROM gold.v_promedio_por_sue")
            prom_sue = cur.fetchone()[0]
            logger.info(f"   v_promedio_por_sue: {prom_sue} grupos")
            
            cur.close()
            
            logger.info(f"\n   ✅ Validación completada")
        
        except Exception as e:
            logger.warning(f"   ⚠️  Error en validación: {e}")
            self.stats["errors"].append(f"Validation: {e}")
    
    def print_summary(self):
        """Resumen de ejecución"""
        logger.info("\n" + "="*70)
        logger.info("📊 RESUMEN DE EJECUCIÓN")
        logger.info("="*70)
        
        logger.info(f"\n   ✅ Bronze loaded: {self.stats['bronze_loaded']}")
        logger.info(f"   ✅ Silver IES loaded: {self.stats['silver_ies_loaded']}")
        logger.info(f"   ✅ Silver Estudiantes loaded: {self.stats['silver_est_loaded']}")
        logger.info(f"   ✅ Silver Docentes loaded: {self.stats['silver_doc_loaded']}")
        logger.info(f"   ✅ Gold loaded: {self.stats['gold_loaded']}")
        
        if self.stats['errors']:
            logger.info(f"\n   ⚠️  Errores ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                logger.info(f"      - {error}")
        
        logger.info(f"\n   Status: {'✅ SUCCESS' if not self.stats['errors'] else '⚠️  WITH WARNINGS'}")
    
    def run(self, csv_file):
        """Ejecutar pipeline completo"""
        logger.info("="*70)
        logger.info("🚀 SNIES ETL LOADER - MEDALLION ARCHITECTURE")
        logger.info("="*70)
        logger.info(f"   CSV: {csv_file}")
        
        try:
            self.connect()
            self.load_bronze(csv_file)
            self.load_silver()
            self.load_gold()
            self.validate_data()
            self.print_summary()
            
            logger.info(f"\n{'='*70}")
            logger.info("✅ ETL COMPLETADO EXITOSAMENTE")
            logger.info(f"{'='*70}\n")
        
        except Exception as e:
            logger.error(f"\n❌ ETL FALLÓ: {e}")
            self.print_summary()
            raise
        
        finally:
            self.disconnect()

def main():
    # Configuración de BD desde variables de entorno (Docker)
    db_host = os.getenv('DB_HOST', 'postgres')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'snies_analytics')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    
    db_connection = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Archivo CSV de entrada
    csv_file = "data/raw/snies_relacion_estudiante_docente.csv"
    
    if not Path(csv_file).exists():
        logger.error(f"❌ CSV no encontrado: {csv_file}")
        sys.exit(1)
    
    # Ejecutar
    loader = SNIESETLLoader(db_connection)
    loader.run(csv_file)

if __name__ == "__main__":
    main()
