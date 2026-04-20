"""
download_snies_automatico.py
Descarga automática de datos SNIES desde datos.gov.co (Socrata API)
Años: 2022-2024
IES: Todas de Bogotá
Métricas: Estudiantes matriculados y Docentes

Uso:
  python download_snies_automatico.py
"""

import requests
import pandas as pd
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SNIESDownloader:
    """Descargador automático de datos SNIES desde Socrata API"""
    
    # URLs de datos.gov.co (Socrata)
    DATASETS = {
        "estudiantes_matriculados": {
            "dataset_id": "32sa-8pi3",
            "nombre": "Estudiantes Matriculados por IES",
            "descripcion": "Total de estudiantes matriculados por institución y año"
        },
        "docentes": {
            "dataset_id": "p7yf-r4ye",
            "nombre": "Personal Docente por IES",
            "descripcion": "Total de docentes por institución y año"
        }
    }
    
    # IES principales de Bogotá
    BOGOTA_CITIES = [
        "BOGOTA", "BOGOTÁ", "Bogota", "Bogotá"
    ]
    
    def __init__(self, output_dir: str = "data/raw", years: List[int] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.years = years or [2022, 2023, 2024]
        self.base_url = "https://www.datos.gov.co/api/views"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SNIES-Analytics/1.0 (Data Engineer)'
        })
    
    def descargar_dataset(self, dataset_key: str, limit: int = 50000) -> Optional[pd.DataFrame]:
        """Descargar un dataset completo de Socrata"""
        
        if dataset_key not in self.DATASETS:
            logger.error(f"❌ Dataset desconocido: {dataset_key}")
            return None
        
        dataset = self.DATASETS[dataset_key]
        dataset_id = dataset["dataset_id"]
        nombre = dataset["nombre"]
        
        logger.info(f"\n📥 Descargando: {nombre}")
        logger.info(f"   Dataset ID: {dataset_id}")
        logger.info(f"   Endpoint: {self.base_url}/{dataset_id}/rows.csv")
        
        try:
            # URL de descarga Socrata (CSV)
            url = f"{self.base_url}/{dataset_id}/rows.csv?accessType=DOWNLOAD&limit={limit}"
            
            logger.info(f"   ⏳ Conectando a Socrata...")
            
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            
            # Guardar CSV temporal
            temp_file = self.output_dir / f"temp_{dataset_key}.csv"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Leer con pandas
            df = pd.read_csv(temp_file, encoding='utf-8')
            
            size_mb = len(response.text) / (1024 * 1024)
            logger.info(f"   ✅ Descargado: {len(df)} registros ({size_mb:.2f} MB)")
            
            # Limpiar temp
            temp_file.unlink()
            
            return df
        
        except requests.exceptions.RequestException as e:
            logger.error(f"   ❌ Error de conexión: {e}")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            return None
    
    def filtrar_bogota_y_anos(self, df: pd.DataFrame, dataset_key: str) -> pd.DataFrame:
        """Filtrar por Bogotá y años 2022-2024"""
        
        logger.info(f"\n🔍 Filtrando datos...")
        logger.info(f"   Registros originales: {len(df)}")
        
        # Normalizar columnas
        df.columns = df.columns.str.strip().str.lower()
        
        logger.info(f"   Columnas encontradas: {df.columns.tolist()}")
        
        # Identificar columna de ciudad/localidad
        ciudad_cols = [col for col in df.columns if 'ciudad' in col or 'localidad' in col or 'municipio' in col]
        ano_cols = [col for col in df.columns if 'año' in col or 'ano' in col or 'year' in col or 'periodo' in col]
        
        logger.info(f"   Columnas de ciudad: {ciudad_cols}")
        logger.info(f"   Columnas de año: {ano_cols}")
        
        df_filtered = df.copy()
        
        # Filtrar por Bogotá
        if ciudad_cols:
            ciudad_col = ciudad_cols[0]
            mask_bogota = df_filtered[ciudad_col].astype(str).str.upper().str.contains('BOGOTA', na=False)
            df_filtered = df_filtered[mask_bogota]
            logger.info(f"   Después de filtrar Bogotá: {len(df_filtered)} registros")
        
        # Filtrar por años
        if ano_cols:
            ano_col = ano_cols[0]
            try:
                df_filtered[ano_col] = pd.to_numeric(df_filtered[ano_col], errors='coerce')
                mask_anos = df_filtered[ano_col].isin(self.years)
                df_filtered = df_filtered[mask_anos]
                logger.info(f"   Después de filtrar años {self.years}: {len(df_filtered)} registros")
            except Exception as e:
                logger.warning(f"   ⚠️  No se pudo filtrar por años: {e}")
        
        return df_filtered
    
    def consolidar_datos(self, df_estudiantes: pd.DataFrame, df_docentes: pd.DataFrame) -> pd.DataFrame:
        """Consolidar estudiantes y docentes en un solo dataframe"""
        
        logger.info(f"\n🔄 Consolidando estudiantes + docentes...")
        
        # Normalizar columnas
        df_est = df_estudiantes.copy()
        df_doc = df_docentes.copy()
        
        df_est.columns = df_est.columns.str.strip().str.lower()
        df_doc.columns = df_doc.columns.str.strip().str.lower()
        
        # Identificar columnas clave
        ies_cols_est = [col for col in df_est.columns if 'institucion' in col or 'ies' in col or 'nombre' in col]
        ies_cols_doc = [col for col in df_doc.columns if 'institucion' in col or 'ies' in col or 'nombre' in col]
        
        ano_cols_est = [col for col in df_est.columns if 'año' in col or 'ano' in col or 'year' in col or 'periodo' in col]
        ano_cols_doc = [col for col in df_doc.columns if 'año' in col or 'ano' in col or 'year' in col or 'periodo' in col]
        
        # Renombrar para merge
        if ies_cols_est:
            df_est = df_est.rename(columns={ies_cols_est[0]: 'ies_name'})
        if ies_cols_doc:
            df_doc = df_doc.rename(columns={ies_cols_doc[0]: 'ies_name'})
        
        if ano_cols_est:
            df_est = df_est.rename(columns={ano_cols_est[0]: 'year'})
        if ano_cols_doc:
            df_doc = df_doc.rename(columns={ano_cols_doc[0]: 'year'})
        
        # Agregación
        agg_est = df_est.groupby(['ies_name', 'year']).size().reset_index(name='total_estudiantes')
        agg_doc = df_doc.groupby(['ies_name', 'year']).size().reset_index(name='total_docentes')
        
        logger.info(f"   IES en estudiantes: {len(agg_est)}")
        logger.info(f"   IES en docentes: {len(agg_doc)}")
        
        # Merge
        consolidated = pd.merge(
            agg_est, 
            agg_doc, 
            on=['ies_name', 'year'], 
            how='outer'
        )
        
        # Calcular ratio
        consolidated['ratio_e_d'] = (
            consolidated['total_estudiantes'] / 
            consolidated['total_docentes']
        ).round(2)
        
        logger.info(f"   ✅ Consolidado: {len(consolidated)} registros")
        
        return consolidated
    
    def descargar_y_consolidar(self) -> Optional[pd.DataFrame]:
        """Descarga completa y consolidación"""
        
        logger.info("=" * 70)
        logger.info("🚀 DESCARGADOR AUTOMÁTICO SNIES")
        logger.info("=" * 70)
        logger.info(f"Años: {self.years}")
        logger.info(f"Localidad: Bogotá")
        logger.info(f"Destino: {self.output_dir}")
        
        # Descargar estudiantes
        df_est = self.descargar_dataset("estudiantes_matriculados")
        if df_est is None:
            logger.error("❌ No se pudo descargar estudiantes")
            return None
        
        # Descargar docentes
        df_doc = self.descargar_dataset("docentes")
        if df_doc is None:
            logger.error("❌ No se pudo descargar docentes")
            return None
        
        # Filtrar por Bogotá y años
        df_est_filtered = self.filtrar_bogota_y_anos(df_est, "estudiantes_matriculados")
        df_doc_filtered = self.filtrar_bogota_y_anos(df_doc, "docentes")
        
        # Consolidar
        if len(df_est_filtered) == 0 or len(df_doc_filtered) == 0:
            logger.warning("⚠️  No hay datos para Bogotá en los años especificados")
            logger.info("   Usando datos de demostración...")
            return None
        
        consolidated = self.consolidar_datos(df_est_filtered, df_doc_filtered)
        
        # Guardar
        output_file = self.output_dir / "snies_descargado.csv"
        consolidated.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"\n💾 Guardado: {output_file}")
        
        # Guardar metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "años": self.years,
            "localidad": "Bogotá",
            "total_registros": len(consolidated),
            "ies_unicas": consolidated['ies_name'].nunique(),
            "archivo": str(output_file)
        }
        
        metadata_file = self.output_dir / "descarga_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📊 RESUMEN:")
        logger.info(f"   Registros totales: {len(consolidated)}")
        logger.info(f"   IES únicas: {consolidated['ies_name'].nunique()}")
        logger.info(f"   Años: {consolidated['year'].unique().tolist()}")
        logger.info(f"   Ratio E/D promedio: {consolidated['ratio_e_d'].mean():.2f}")
        
        logger.info(f"\n✅ DESCARGA COMPLETADA EXITOSAMENTE")
        logger.info(f"   Datos listos en: {output_file}")
        
        return consolidated


def main():
    """Función principal"""
    
    # Crear descargador
    downloader = SNIESDownloader(
        output_dir="data/raw",
        years=[2022, 2023, 2024]
    )
    
    # Descargar y consolidar
    df = downloader.descargar_y_consolidar()
    
    if df is not None:
        logger.info(f"\n✅ Listo para usar con docker-compose up")
    else:
        logger.warning(f"\n⚠️  Advertencia: usando datos de demostración")


if __name__ == "__main__":
    main()
