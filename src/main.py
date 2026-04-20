"""
main.py - Pipeline ETL Principal SNIES
Ingesta → Transformación → Loading → Validación
"""

import logging
import sys
from pathlib import Path

# Agregar rutas
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DATABASE_URL, RAW_DATA_DIR, SUE_INSTITUTIONS
from src.snies_loader import SNIESLoader
from src.transformation import SNIESTransformer
from src.db_loader import PostgreSQLLoader

logger = logging.getLogger(__name__)

def main():
    """Ejecutar pipeline completo"""
    
    logger.info("="*70)
    logger.info("🚀 SNIES ANALYTICS - PIPELINE ETL")
    logger.info("="*70)
    
    try:
        # ===== FASE 1: INGESTA =====
        logger.info("\n📥 FASE 1: INGESTA")
        logger.info("-" * 70)
        
        loader = SNIESLoader(RAW_DATA_DIR)
        df_raw = loader.load_all()
        validation = loader.validate_structure(df_raw)
        loader.print_validation_report(validation)
        
        # ===== FASE 2: TRANSFORMACIÓN =====
        logger.info("\n🔄 FASE 2: TRANSFORMACIÓN")
        logger.info("-" * 70)
        
        transformer = (
            SNIESTransformer(df_raw)
            .clean()
            .normalize_ies_names()
            .enrich_with_teachers()
            .add_sue_classification(SUE_INSTITUTIONS)
            .validate_ranges()
        )
        
        df_transformed = transformer.get_result()
        transformer.print_summary()
        
        # ===== FASE 3: LOADING =====
        logger.info("\n💾 FASE 3: LOADING")
        logger.info("-" * 70)
        
        db_loader = PostgreSQLLoader(DATABASE_URL)
        
        # Leer schema
        schema_file = Path(__file__).parent.parent / "sql" / "schema.sql"
        if schema_file.exists():
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            logger.info("📋 Creando esquema...")
            db_loader.create_schema(schema_sql)
        else:
            logger.warning(f"⚠️  Schema no encontrado en {schema_file}")
        
        # Insertar datos
        logger.info("\n📥 Insertando datos en PostgreSQL...")
        rows_inserted = db_loader.insert_data(df_transformed, 'snies_consolidated', if_exists='replace')
        logger.info(f"✅ {rows_inserted} registros insertados")
        
        # ===== FASE 4: VALIDACIÓN =====
        logger.info("\n✅ FASE 4: VALIDACIÓN POST-CARGA")
        logger.info("-" * 70)
        
        checks = db_loader.run_data_quality_checks('snies_consolidated')
        db_loader.print_quality_report(checks)
        
        db_loader.close()
        
        # ===== RESUMEN FINAL =====
        logger.info("\n" + "="*70)
        logger.info("✅ PIPELINE COMPLETADO EXITOSAMENTE")
        logger.info("="*70)
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Error en pipeline: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    exit_code = main()
    sys.exit(exit_code)
