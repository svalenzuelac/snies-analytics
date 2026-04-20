"""
cargador_etl.py
ETL para SNIES Analytics - Arquitectura Medallion
Flujo: CSV (crudo) -> Bronce -> Plata -> Oro
"""

import subprocess
import sys

print("=" * 70)
print("Instalando dependencias...")
print("=" * 70)

subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", 
                       "psycopg2-binary", "pandas", "sqlalchemy"])

print("Dependencias instaladas\n")

import psycopg2
from psycopg2.extras import execute_batch
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CargadorSNIES:
    """Cargador ETL para SNIES Analytics"""
    
    def __init__(self, cadena_conexion_bd):
        self.cadena_conexion = cadena_conexion_bd
        self.conexion = None
        self.estadisticas = {
            "bronce_cargado": 0,
            "plata_ies_cargado": 0,
            "plata_est_cargado": 0,
            "plata_doc_cargado": 0,
            "oro_cargado": 0,
            "errores": []
        }
    
    def conectar(self):
        try:
            self.conexion = psycopg2.connect(self.cadena_conexion)
            logger.info("Conectado a PostgreSQL")
        except Exception as e:
            logger.error("Error de conexión: " + str(e))
            raise
    
    def desconectar(self):
        if self.conexion:
            self.conexion.close()
            logger.info("Conexión cerrada")
    
    def registrar_auditoria(self, etapa, estado, mensaje, registros_afectados):
        try:
            cur = self.conexion.cursor()
            cur.execute("""
                INSERT INTO auditoria.registro_pipeline 
                (etapa, estado, mensaje, registros_afectados, inicio_at, fin_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (etapa, estado, mensaje, registros_afectados))
            self.conexion.commit()
            cur.close()
        except Exception as e:
            logger.warning("No se pudo registrar auditoría: " + str(e))
    
    def cargar_bronce(self, archivo_csv):
        logger.info("=" * 70)
        logger.info("FASE 1: CARGANDO BRONCE (CRUDO)")
        logger.info("=" * 70)
        
        try:
            df = pd.read_csv(archivo_csv, dtype=str)
            logger.info("CSV leído: " + str(len(df)) + " registros")
            
            df = df.fillna('')
            
            registros = []
            for idx, fila in df.iterrows():
                try:
                    estudiantes = int(fila['total_estudiantes']) if fila['total_estudiantes'] else None
                    docentes = int(fila['total_docentes']) if fila['total_docentes'] else None
                    ratio = float(fila['estudiantes_por_docente']) if fila['estudiantes_por_docente'] else None
                    
                    registros.append((
                        fila['nombre_ies'],
                        int(fila['año']),
                        estudiantes,
                        docentes,
                        ratio,
                        fila['sector_ies'],
                        fila['clasificacion_sue'],
                        Path(archivo_csv).name
                    ))
                except Exception as e:
                    logger.warning("Error en fila " + str(idx) + ": " + str(e))
                    self.estadisticas["errores"].append("Fila " + str(idx) + ": " + str(e))
            
            cur = self.conexion.cursor()
            cur.execute("TRUNCATE TABLE bronce.snies_crudo")
            
            execute_batch(cur, """
                INSERT INTO bronce.snies_crudo 
                (nombre_ies, año, total_estudiantes, total_docentes, 
                 estudiantes_por_docente, sector_ies, clasificacion_sue, archivo_fuente)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, registros, page_size=1000)
            
            self.conexion.commit()
            self.estadisticas["bronce_cargado"] = len(registros)
            
            logger.info(str(len(registros)) + " registros cargados en bronce")
            self.registrar_auditoria("bronce", "exito", "Cargados " + str(len(registros)) + " registros", len(registros))
            
            cur.close()
        
        except Exception as e:
            logger.error("Error cargando bronce: " + str(e))
            self.estadisticas["errores"].append("Bronce: " + str(e))
            self.registrar_auditoria("bronce", "error", str(e), 0)
            raise
    
    def cargar_plata(self):
        logger.info("=" * 70)
        logger.info("FASE 2: CARGANDO PLATA (PROCESADA)")
        logger.info("=" * 70)
        
        try:
            cur = self.conexion.cursor()
            
            logger.info("Cargando plata.snies_ies...")
            
            cur.execute("TRUNCATE TABLE plata.snies_ies CASCADE")
            
            cur.execute("""
                INSERT INTO plata.snies_ies (nombre_ies, sector_ies, es_sue)
                SELECT DISTINCT 
                    nombre_ies,
                    sector_ies,
                    CASE 
                        WHEN clasificacion_sue = 'SUE' THEN TRUE 
                        ELSE FALSE 
                    END
                FROM bronce.snies_crudo
                ON CONFLICT (nombre_ies) DO NOTHING
            """)
            
            cantidad_ies = cur.rowcount
            self.estadisticas["plata_ies_cargado"] = cantidad_ies
            logger.info(str(cantidad_ies) + " IES cargadas")
            
            logger.info("Cargando plata.snies_estudiantes...")
            
            cur.execute("TRUNCATE TABLE plata.snies_estudiantes CASCADE")
            
            cur.execute("""
                INSERT INTO plata.snies_estudiantes (ies_id, año, total_estudiantes)
                SELECT 
                    s.ies_id,
                    b.año,
                    b.total_estudiantes
                FROM bronce.snies_crudo b
                JOIN plata.snies_ies s ON b.nombre_ies = s.nombre_ies
                WHERE b.total_estudiantes IS NOT NULL
                ON CONFLICT (ies_id, año) DO UPDATE SET total_estudiantes = EXCLUDED.total_estudiantes
            """)
            
            cantidad_est = cur.rowcount
            self.estadisticas["plata_est_cargado"] = cantidad_est
            logger.info(str(cantidad_est) + " registros de estudiantes cargados")
            
            logger.info("Cargando plata.snies_docentes...")
            
            cur.execute("TRUNCATE TABLE plata.snies_docentes CASCADE")
            
            cur.execute("""
                INSERT INTO plata.snies_docentes (ies_id, año, total_docentes)
                SELECT 
                    s.ies_id,
                    b.año,
                    b.total_docentes
                FROM bronce.snies_crudo b
                JOIN plata.snies_ies s ON b.nombre_ies = s.nombre_ies
                WHERE b.total_docentes IS NOT NULL
                ON CONFLICT (ies_id, año) DO UPDATE SET total_docentes = EXCLUDED.total_docentes
            """)
            
            cantidad_doc = cur.rowcount
            self.estadisticas["plata_doc_cargado"] = cantidad_doc
            logger.info(str(cantidad_doc) + " registros de docentes cargados")
            
            self.conexion.commit()
            logger.info("PLATA completada")
            self.registrar_auditoria("plata", "exito", "Capas plata cargadas", cantidad_ies + cantidad_est + cantidad_doc)
            
            cur.close()
        
        except Exception as e:
            logger.error("Error cargando plata: " + str(e))
            self.estadisticas["errores"].append("Plata: " + str(e))
            self.registrar_auditoria("plata", "error", str(e), 0)
            raise
    
    def cargar_oro(self):
        logger.info("=" * 70)
        logger.info("FASE 3: CARGANDO ORO (ANALÍTICA)")
        logger.info("=" * 70)
        
        try:
            cur = self.conexion.cursor()
            
            logger.info("Cargando oro.dim_ies...")
            
            cur.execute("TRUNCATE TABLE oro.hecho_relacion_estudiante_docente CASCADE")
            cur.execute("TRUNCATE TABLE oro.dim_ies CASCADE")
            
            cur.execute("""
                INSERT INTO oro.dim_ies (ies_id, nombre_ies, sector_ies, es_sue)
                SELECT ies_id, nombre_ies, sector_ies, es_sue
                FROM plata.snies_ies
                ON CONFLICT (ies_id) DO UPDATE SET 
                    nombre_ies = EXCLUDED.nombre_ies,
                    sector_ies = EXCLUDED.sector_ies,
                    es_sue = EXCLUDED.es_sue
            """)
            
            cantidad_dim_ies = cur.rowcount
            logger.info(str(cantidad_dim_ies) + " IES en dimensión")
            
            logger.info("Cargando oro.hecho_relacion_estudiante_docente...")
            
            cur.execute("""
                INSERT INTO oro.hecho_relacion_estudiante_docente
                (dim_ies_id, dim_tiempo_id, total_estudiantes, total_docentes, estudiantes_por_docente)
                SELECT
                    d.dim_ies_id,
                    t.dim_tiempo_id,
                    COALESCE(e.total_estudiantes, 0),
                    COALESCE(doc.total_docentes, 0),
                    CASE
                        WHEN COALESCE(doc.total_docentes, 0) > 0
                        THEN ROUND(COALESCE(e.total_estudiantes, 0)::DECIMAL / doc.total_docentes, 2)
                        ELSE NULL
                    END
                FROM oro.dim_ies d
                CROSS JOIN oro.dim_tiempo t
                LEFT JOIN plata.snies_estudiantes e ON d.ies_id = e.ies_id AND t.año = e.año
                LEFT JOIN plata.snies_docentes doc ON d.ies_id = doc.ies_id AND t.año = doc.año
                WHERE d.esta_activo = TRUE
                ON CONFLICT (dim_ies_id, dim_tiempo_id) DO UPDATE SET
                    total_estudiantes = EXCLUDED.total_estudiantes,
                    total_docentes = EXCLUDED.total_docentes,
                    estudiantes_por_docente = EXCLUDED.estudiantes_por_docente,
                    actualizado_at = CURRENT_TIMESTAMP
            """)
            
            cantidad_hecho = cur.rowcount
            self.estadisticas["oro_cargado"] = cantidad_hecho
            logger.info(str(cantidad_hecho) + " hechos cargados")
            
            self.conexion.commit()
            logger.info("ORO completada")
            self.registrar_auditoria("oro", "exito", "Capa oro cargada", cantidad_hecho)
            
            cur.close()
        
        except Exception as e:
            logger.error("Error cargando oro: " + str(e))
            self.estadisticas["errores"].append("Oro: " + str(e))
            self.registrar_auditoria("oro", "error", str(e), 0)
            raise
    
    def validar_datos(self):
        logger.info("=" * 70)
        logger.info("VALIDACIÓN DE DATOS")
        logger.info("=" * 70)
        
        try:
            cur = self.conexion.cursor()
            
            cur.execute("SELECT COUNT(*) FROM bronce.snies_crudo")
            bronce_count = cur.fetchone()[0]
            logger.info("bronce.snies_crudo: " + str(bronce_count) + " registros")
            
            cur.execute("SELECT COUNT(*) FROM plata.snies_ies")
            ies_count = cur.fetchone()[0]
            logger.info("plata.snies_ies: " + str(ies_count) + " IES")
            
            cur.execute("SELECT COUNT(*) FROM plata.snies_estudiantes")
            est_count = cur.fetchone()[0]
            logger.info("plata.snies_estudiantes: " + str(est_count) + " registros")
            
            cur.execute("SELECT COUNT(*) FROM plata.snies_docentes")
            doc_count = cur.fetchone()[0]
            logger.info("plata.snies_docentes: " + str(doc_count) + " registros")
            
            cur.execute("SELECT COUNT(*) FROM oro.hecho_relacion_estudiante_docente")
            hecho_count = cur.fetchone()[0]
            logger.info("oro.hecho_relacion_estudiante_docente: " + str(hecho_count) + " hechos")
            
            logger.info("Validación completada")
            cur.close()
        
        except Exception as e:
            logger.warning("Error en validación: " + str(e))
            self.estadisticas["errores"].append("Validación: " + str(e))
    
    def imprimir_resumen(self):
        logger.info("=" * 70)
        logger.info("RESUMEN DE EJECUCIÓN")
        logger.info("=" * 70)
        
        logger.info("Bronce cargado: " + str(self.estadisticas['bronce_cargado']))
        logger.info("Plata IES cargado: " + str(self.estadisticas['plata_ies_cargado']))
        logger.info("Plata Estudiantes cargado: " + str(self.estadisticas['plata_est_cargado']))
        logger.info("Plata Docentes cargado: " + str(self.estadisticas['plata_doc_cargado']))
        logger.info("Oro cargado: " + str(self.estadisticas['oro_cargado']))
        
        if self.estadisticas['errores']:
            logger.info("Errores: " + str(len(self.estadisticas['errores'])))
            for error in self.estadisticas['errores']:
                logger.info("  - " + error)
        
        estado_final = "EXITO" if not self.estadisticas['errores'] else "CON ADVERTENCIAS"
        logger.info("Estado: " + estado_final)
    
    def ejecutar(self, archivo_csv):
        logger.info("=" * 70)
        logger.info("CARGADOR SNIES - ARQUITECTURA MEDALLION")
        logger.info("=" * 70)
        logger.info("CSV: " + archivo_csv)
        
        try:
            self.conectar()
            self.cargar_bronce(archivo_csv)
            self.cargar_plata()
            self.cargar_oro()
            self.validar_datos()
            self.imprimir_resumen()
            
            logger.info("=" * 70)
            logger.info("ETL COMPLETADO EXITOSAMENTE")
            logger.info("=" * 70)
        
        except Exception as e:
            logger.error("ETL FALLÓ: " + str(e))
            self.imprimir_resumen()
            raise
        
        finally:
            self.desconectar()

def main():
    bd_host = os.getenv('BD_HOST', 'postgres')
    bd_puerto = os.getenv('BD_PUERTO', '5432')
    bd_nombre = os.getenv('BD_NOMBRE', 'snies_analisis')
    bd_usuario = os.getenv('BD_USUARIO', 'postgres')
    bd_contrasena = os.getenv('BD_CONTRASENA', 'postgres')
    
    cadena_conexion = "postgresql://" + bd_usuario + ":" + bd_contrasena + "@" + bd_host + ":" + bd_puerto + "/" + bd_nombre
    
    archivo_csv = "data/snies_relacion_estudiante_docente.csv"
    
    if not Path(archivo_csv).exists():
        logger.error("CSV no encontrado: " + archivo_csv)
        sys.exit(1)
    
    cargador = CargadorSNIES(cadena_conexion)
    cargador.ejecutar(archivo_csv)

if __name__ == "__main__":
    main()
