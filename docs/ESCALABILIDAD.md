# 📈 Plan de Escalabilidad

Estrategia para escalar SNIES Analytics de Bogotá a nivel nacional y prepararse para crecimiento futuro.

---

## 🎯 Visión General

### Fase Actual (v2.0)
- **Alcance**: Bogotá D.C.
- **Instituciones**: 117 IES
- **Período**: 2022-2024 (3 años)
- **Registros**: 351
- **Plataforma**: PostgreSQL monolítico
- **Orquestación**: Docker Compose

### Fase Target (v3.0+)
- **Alcance**: Colombia completa
- **Instituciones**: ~1,700 IES
- **Período**: 2015-2025+ (11+ años)
- **Registros**: ~18,700
- **Plataforma**: Data Lake + Warehouse
- **Orquestación**: Airflow + Kubernetes

---

## 📊 Análisis de Volumen

### Estimaciones

| Parámetro | Bogotá (Actual) | Colombia (Target) | Factor |
|-----------|----------------|--------------------|--------|
| **IES** | 117 | ~1,700 | 14x |
| **Años** | 3 | 11 | 4x |
| **Registros** | 351 | ~18,700 | 53x |
| **GB Almacenamiento** | 0.05 | 2-3 | 50x |
| **Queries/mes** | 1,000 | 100,000 | 100x |
| **Usuarios** | 10 | 500+ | 50x |

### Performance Esperado

```
Escenario: Bogotá (ACTUAL)
├─ Query simple: 5ms
├─ Agregación: 20ms
├─ Full scan: 100ms
└─ Dashboard load: 500ms

Escenario: Colombia (SIN OPTIMIZAR)
├─ Query simple: 2,650ms (530x lento)
├─ Agregación: 10,600ms (530x lento)
├─ Full scan: 53,000ms (530x lento)
└─ Dashboard load: 265,000ms (530x lento) ❌

Escenario: Colombia (OPTIMIZADO)
├─ Query simple: 10ms ✅
├─ Agregación: 50ms ✅
├─ Full scan: 500ms ✅
└─ Dashboard load: 1,000ms ✅
```

---

## 🔄 Roadmap de Escalabilidad

### Timeline Recomendado

```
Hoy (Abril 2026)
│
├─ Mes 1-2: Preparar infraestructura
│   ├─ Agregar dimensión 'departamento'
│   ├─ Implementar particionamiento
│   └─ Configurar Airflow
│
├─ Mes 3-4: Ingerir datos regionales
│   ├─ Scripts para cada región
│   ├─ Validación de integridad
│   └─ Backfill histórico
│
├─ Mes 5-6: Optimización y tuning
│   ├─ Índices por región
│   ├─ Caché distribuido
│   └─ Load testing
│
└─ Mes 7+: Monitoreo en producción
    ├─ Alertas automáticas
    ├─ SLA monitoring
    └─ Continuous improvement
```

---

## 🔧 Cambios Técnicos Requeridos

### 1. Agregar Dimensión Geográfica

#### 1.1 Schema Update

```sql
-- Nueva tabla de dimensión
CREATE TABLE oro.dim_departamento (
    id SERIAL PRIMARY KEY,
    nombre_departamento VARCHAR(100) UNIQUE,
    region_geografica VARCHAR(50),
    poblacion_estudiantes INT,
    num_ies INT,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar datos
INSERT INTO oro.dim_departamento VALUES
(1, 'Bogotá', 'Centro', 850000, 117),
(2, 'Antioquia', 'Norte', 450000, 85),
(3, 'Valle del Cauca', 'Occidente', 320000, 52),
...

-- Modificar tabla de hechos
ALTER TABLE oro.fact_relacion_estudiante_docente
ADD COLUMN dim_departamento_id INT,
ADD CONSTRAINT fk_fact_depto 
    FOREIGN KEY (dim_departamento_id) 
    REFERENCES oro.dim_departamento(id);

-- Índice de performance
CREATE INDEX idx_fact_depto 
ON oro.fact_relacion_estudiante_docente(dim_departamento_id);
```

#### 1.2 Update en Python

```python
def cargar_datos_nacional():
    """Carga datos de todas las regiones"""
    departamentos = ['Bogotá', 'Antioquia', 'Valle', ...]
    
    for dept in departamentos:
        df = descargar_snies_por_region(dept)
        dim_dept_id = get_departamento_id(dept)
        
        for idx, row in df.iterrows():
            fact = {
                'dim_ies_id': row['ies_id'],
                'dim_tiempo_id': row['año'],
                'dim_departamento_id': dim_dept_id,  # NUEVO
                'ratio_estudiante_docente': row['ratio'],
                ...
            }
            session.add(FactRelacion(**fact))
    
    session.commit()
```

### 2. Implementar Particionamiento

#### 2.1 Partición por Año

```sql
-- Crear tabla particionada
CREATE TABLE oro.fact_relacion_estudiante_docente_partitioned (
    id SERIAL,
    dim_ies_id INT,
    dim_tiempo_id INT,
    dim_departamento_id INT,
    total_estudiantes INT,
    total_docentes INT,
    ratio_estudiante_docente DECIMAL,
    creado_at TIMESTAMP,
    actualizado_at TIMESTAMP
) PARTITION BY RANGE (dim_tiempo_id);

-- Crear particiones por año
CREATE TABLE fact_2022 PARTITION OF 
    oro.fact_relacion_estudiante_docente_partitioned
FOR VALUES FROM (1) TO (2);

CREATE TABLE fact_2023 PARTITION OF 
    oro.fact_relacion_estudiante_docente_partitioned
FOR VALUES FROM (2) TO (3);

CREATE TABLE fact_2024 PARTITION OF 
    oro.fact_relacion_estudiante_docente_partitioned
FOR VALUES FROM (3) TO (4);

-- Beneficios
-- • Queries filtrando por año: 10x más rápidas
-- • Backup selectivo: solo años requeridos
-- • Mantenimiento: solo una partición a la vez
-- • Escalabilidad: agregar años es trivial
```

#### 2.2 Partición por Departamento (Alternativa)

```sql
-- Más avanzado: hash partitioning
CREATE TABLE oro.fact_relacion_estudiante_docente_hash (
    ...
) PARTITION BY HASH (dim_departamento_id);

-- Crear 5 particiones (una por región)
CREATE TABLE fact_region_1 PARTITION OF ... WITH (modulus 5, remainder 0);
CREATE TABLE fact_region_2 PARTITION OF ... WITH (modulus 5, remainder 1);
...
```

### 3. Configurar Airflow

#### 3.1 Instalación

```bash
# Instalar Airflow
pip install apache-airflow

# Inicializar
airflow db init

# Crear usuario admin
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Iniciar
airflow webserver
airflow scheduler
```

#### 3.2 DAG de Orquestación

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-team',
    'start_date': datetime(2026, 4, 20),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'snies_etl_pipeline',
    default_args=default_args,
    description='ETL completo SNIES Nacional',
    schedule_interval='@weekly',  # Ejecutar semanalmente
    catchup=False,
)

# Task 1: Descargar datos
descargar = PythonOperator(
    task_id='descargar_snies',
    python_callable=descargador_snies_produccion_final,
    op_kwargs={'años': [2022, 2023, 2024]},
    dag=dag,
)

# Task 2: Validar datos
validar = BashOperator(
    task_id='validar_datos',
    bash_command='python scripts/validar_integridad.py',
    dag=dag,
)

# Task 3: Cargar Bronce
cargar_bronce = PythonOperator(
    task_id='cargar_bronce',
    python_callable=cargar_fase_bronce,
    dag=dag,
)

# Task 4: Cargar Plata
cargar_plata = PythonOperator(
    task_id='cargar_plata',
    python_callable=cargar_fase_plata,
    dag=dag,
)

# Task 5: Cargar Oro
cargar_oro = PythonOperator(
    task_id='cargar_oro',
    python_callable=cargar_fase_oro,
    dag=dag,
)

# Task 6: Notificar
notificar = BashOperator(
    task_id='notificar_completado',
    bash_command='echo "Pipeline completado" | mail -s "SNIES ETL OK" admin@example.com',
    dag=dag,
)

# Definir dependencias
descargar >> validar >> cargar_bronce >> cargar_plata >> cargar_oro >> notificar
```

### 4. Migrar a Data Lake (S3)

#### 4.1 Estructura de Buckets

```
s3://snies-analytics-datalake/
├── raw/  (Datos sin procesar)
│   ├── 2022/
│   │   ├── bogota/
│   │   ├── antioquia/
│   │   └── ...
│   ├── 2023/
│   └── 2024/
│
├── processed/  (Datos transformados)
│   ├── bronce/
│   ├── plata/
│   └── oro/
│
└── metadata/
    ├── schemas.json
    ├── data_quality_reports/
    └── audit_logs/
```

#### 4.2 Código de Upload

```python
import boto3
import pandas as pd
from datetime import datetime

s3 = boto3.client('s3')

def upload_to_datalake(df, año, departamento, phase):
    """
    Sube DataFrame a Data Lake
    
    Args:
        df: DataFrame procesado
        año: Año de datos
        departamento: Región (ej: 'bogota')
        phase: 'raw', 'processed', 'oro'
    """
    bucket = 'snies-analytics-datalake'
    key = f"{phase}/{año}/{departamento}/datos_{datetime.now().isoformat()}.parquet"
    
    # Guardar como parquet (mejor compresión)
    df.to_parquet(f"/tmp/{key.split('/')[-1]}")
    
    # Subir a S3
    s3.upload_file(
        f"/tmp/{key.split('/')[-1]}",
        bucket,
        key,
        ExtraArgs={'ContentType': 'application/octet-stream'}
    )
    
    return f"s3://{bucket}/{key}"
```

### 5. Implementar Spark

#### 5.1 PySpark ETL

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count, avg
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("SNIES_SPARK_ETL") \
    .config("spark.sql.shuffle.partitions", 200) \
    .getOrCreate()

# Leer datos masivos
df_raw = spark.read.parquet("s3://snies-analytics-datalake/raw/**/*.parquet")

# Transformaciones distribuidas
df_bronce = df_raw \
    .withColumn("cargado_at", F.current_timestamp()) \
    .write.parquet("s3://snies-analytics-datalake/bronce/")

df_plata = spark.sql("""
    SELECT 
        DISTINCT nombre_ies,
        sector_ies,
        es_sue,
        año,
        SUM(total_estudiantes) as estudiantes_totales,
        SUM(total_docentes) as docentes_totales
    FROM df_bronce
    GROUP BY nombre_ies, sector_ies, es_sue, año
""")

# Calcular ratios con Window Functions
window_spec = Window.partitionBy("nombre_ies").orderBy("año")
df_oro = df_plata \
    .withColumn("ratio", col("estudiantes_totales") / col("docentes_totales")) \
    .withColumn("variacion_anual", 
        col("ratio") - lag("ratio").over(window_spec))

df_oro.write.parquet("s3://snies-analytics-datalake/oro/")
```

---

## 🚀 Implementación por Fases

### Fase 1: Preparación (Mes 1-2)

```sql
-- 1. Agregar columnas
ALTER TABLE oro.dim_ies ADD COLUMN departamento VARCHAR(100);
ALTER TABLE oro.dim_ies ADD COLUMN codigo_dane INT;

-- 2. Crear índices adicionales
CREATE INDEX idx_dim_ies_dept ON oro.dim_ies(departamento);

-- 3. Crear tabla de audit ampliada
ALTER TABLE auditoria.registro_pipeline 
ADD COLUMN departamentos_procesados INT[],
ADD COLUMN ies_procesadas INT;

-- 4. Agregar schema para España y otras regiones
CREATE SCHEMA IF NOT EXISTS plata_regional;
CREATE SCHEMA IF NOT EXISTS oro_regional;
```

### Fase 2: Ingesta Regional (Mes 3-4)

```python
def ingestar_por_region(regiones=['ANTIOQUIA', 'VALLE', 'ATLÁNTICO']):
    """
    Descarga y procesa datos por región en paralelo
    """
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                descargador_snies_produccion_final,
                región=región
            )
            for región in regiones
        ]
        
        for future in futures:
            df = future.result()
            cargar_etl(df)
```

### Fase 3: Optimización (Mes 5-6)

```python
# Crear índices paralelos
SQL_QUERIES = [
    "CREATE INDEX CONCURRENTLY idx_fact_depto ON oro.fact_relacion_estudiante_docente(dim_departamento_id);",
    "CREATE INDEX CONCURRENTLY idx_fact_año ON oro.fact_relacion_estudiante_docente(dim_tiempo_id);",
    "VACUUM ANALYZE oro.fact_relacion_estudiante_docente;",
]

from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    for query in SQL_QUERIES:
        executor.submit(execute_sql, query)
```

---

## 📊 Métricas de Éxito

| Métrica | Actual | Target | Plazo |
|---------|--------|--------|-------|
| **Cobertura Geográfica** | Bogotá | Colombia | 6 meses |
| **Instituciones** | 117 | 1,700 | 6 meses |
| **Query Latency (p99)** | 100ms | 500ms | 3 meses |
| **Uptime** | 99.5% | 99.95% | 9 meses |
| **Data Freshness** | Semanal | Diaria | 4 meses |
| **Usuarios Activos** | 10 | 200+ | 12 meses |
| **Dashboard Availability** | 99.5% | 99.95% | 6 meses |

---

## 💰 Estimación de Costos

### Infraestructura Cloud (AWS)

```
OPCIÓN 1: PostgreSQL Managed (RDS)
├─ db.t3.medium (2 vCPU, 4GB RAM): $250/mes
├─ Storage 500GB: $50/mes
├─ Backup automático: $50/mes
└─ TOTAL: $350/mes

OPCIÓN 2: Redshift (Warehouse)
├─ dc2.large (2 nodos): $1,500/mes
├─ Storage incluido (160GB/nodo)
├─ Backup: $100/mes
└─ TOTAL: $1,600/mes

OPCIÓN 3: Data Lake (S3 + Lambda + Athena)
├─ S3 Storage 10TB: $250/mes
├─ Athena queries: $5 per TB scanned = $100/mes
├─ Lambda processing: $100/mes
└─ TOTAL: $450/mes

OPCIÓN 4: Hybrid (Recomendado)
├─ PostgreSQL RDS: $350/mes
├─ Data Lake S3: $250/mes
├─ Airflow EC2: $150/mes
└─ TOTAL: $750/mes (vs $2,000+ Snowflake)
```

---

## ✅ Checklist de Escalabilidad

- [ ] Agregar dimensión departamento
- [ ] Implementar particionamiento
- [ ] Configurar Airflow
- [ ] Setup Data Lake (S3)
- [ ] Migrar a Spark
- [ ] Implementar caché (Redis)
- [ ] Setup monitoreo (Prometheus)
- [ ] Crear alertas automáticas
- [ ] Capacitación del equipo
- [ ] Documentar nuevas arquitecturas

---

## 📚 Referencias

- [AWS Data Lake](https://aws.amazon.com/solutions/implementations/data-lake-aws-structure/)
- [Apache Airflow](https://airflow.apache.org/)
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [PostgreSQL Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [Data Warehouse Best Practices](https://cloud.google.com/solutions/data-warehouse)

---

**Versión**: 2.0  
**Última actualización**: Abril 2026  
**Próxima revisión**: Septiembre 2026
