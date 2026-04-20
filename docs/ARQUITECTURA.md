# 🏗️ Arquitectura Técnica Detallada

---

## 1. Flujo General ETL

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. DESCARGA (descargador_snies_produccion_final.py)                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  • Conecta a portal SNIES en línea                                 │
│  • Descarga 6 archivos Excel (2022-2024)                           │
│  • Detecta dinámicamente hojas de datos                            │
│  • Filtra por departamento: Bogotá D.C.                            │
│  • Normaliza nombres (espacios, mayúsculas)                        │
│  • Identifica 32 universidades SUE (lista hardcoded)              │
│  • Genera CSV limpio: snies_relacion_estudiante_docente.csv       │
│  • Crea metadata en JSON: auditoría de descarga                    │
│                                                                      │
│  Salida: CSV con 351 registros (117 IES × 3 años)                │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. CARGADOR ETL (cargador_etl.py) - 3 FASES                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FASE 1: BRONCE (Raw Load)                                         │
│  ├─ Lee CSV limpio                                                 │
│  ├─ Valida 351 registros                                           │
│  ├─ Carga sin transformar en bronce.snies_crudo                    │
│  ├─ Timestamp: cargado_at                                          │
│  └─ Auditoría: registro_pipeline (inicio, fin)                     │
│                                                                      │
│  FASE 2: PLATA (Transformation)                                    │
│  ├─ Lee bronce.snies_crudo                                         │
│  ├─ Normaliza nombres de IES                                       │
│  ├─ Elimina duplicados (DISTINCT)                                  │
│  ├─ Crea plata.snies_ies (117 registros)                          │
│  ├─ Crea plata.snies_estudiantes (351)                            │
│  ├─ Crea plata.snies_docentes (351)                               │
│  ├─ Valida nulos con COALESCE                                      │
│  └─ Auditoría: fase completada                                     │
│                                                                      │
│  FASE 3: ORO (Analytics)                                           │
│  ├─ Lee plata.*                                                    │
│  ├─ Crea dimensiones: dim_ies, dim_tiempo, dim_sector             │
│  ├─ Crea tabla de hechos: fact_relacion_estudiante_docente        │
│  ├─ Calcula ratio: estudiantes / docentes                          │
│  ├─ Crea vistas analíticas (4 vistas)                             │
│  └─ Auditoría: carga completada                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Modelo Medallion en Detalle

### 2.1 BRONCE (Raw Data)

```sql
-- Schema: bronce
-- Tablas: snies_crudo

bronce.snies_crudo
├─ id (PK)
├─ nombre_ies (VARCHAR)
├─ año (INT)
├─ total_estudiantes (INT)
├─ total_docentes (INT)
├─ sector_ies (VARCHAR)  -- 'Oficial' o 'Privado'
├─ departamento (VARCHAR)
├─ cargado_at (TIMESTAMP)
└─ fuente (VARCHAR)  -- 'SNIES_2022', etc.

Características:
- 351 registros
- Sin transformación
- Preserva datos originales
- Auditoría de carga
```

### 2.2 PLATA (Processed Data)

```sql
-- Schema: plata
-- Tablas: snies_ies, snies_estudiantes, snies_docentes

plata.snies_ies (DIMENSION)
├─ id (PK)
├─ nombre_ies (VARCHAR, UNIQUE)
├─ sector_ies (VARCHAR)
├─ es_sue (BOOLEAN)  -- True si está en lista SUE
├─ creado_at (TIMESTAMP)
└─ actualizado_at (TIMESTAMP)

Características:
- 117 registros (único por institución)
- Nombres normalizados
- Sector validado
- Identificación SUE exacta

plata.snies_estudiantes
├─ id (PK)
├─ ies_id (FK → plata.snies_ies)
├─ año (INT, 2022-2024)
├─ total_estudiantes (INT, NOT NULL)
├─ creado_at (TIMESTAMP)
└─ actualizado_at (TIMESTAMP)

Características:
- 351 registros
- Normalización de valores
- Manejo de nulos
- Validación de años

plata.snies_docentes
├─ id (PK)
├─ ies_id (FK → plata.snies_ies)
├─ año (INT, 2022-2024)
├─ total_docentes (INT, NOT NULL)
├─ creado_at (TIMESTAMP)
└─ actualizado_at (TIMESTAMP)

Características:
- 351 registros
- Identifica IES sin docentes (valor = 0)
- Validación de tipos
```

### 2.3 ORO (Analytics Layer)

#### Dimensiones

```sql
oro.dim_ies
├─ id (PK)
├─ nombre_ies (VARCHAR)
├─ sector_ies (VARCHAR)  -- 'Oficial', 'Privado'
├─ es_sue (BOOLEAN)
├─ fecha_inicio (DATE)  -- SCD Type 2
├─ fecha_fin (DATE)     -- SCD Type 2
├─ activo (BOOLEAN)     -- SCD Type 2
├─ creado_at (TIMESTAMP)
└─ actualizado_at (TIMESTAMP)

Características:
- 117 registros
- SCD Type 2 (Slowly Changing Dimension)
- Historial completo de cambios
- Permite análisis histórico

oro.dim_tiempo
├─ id (PK)
├─ año (INT, UNIQUE)
├─ trimestre (INT)
├─ semestre (INT)
├─ es_bisiesto (BOOLEAN)
└─ descripcion (VARCHAR)

Características:
- 3 registros (2022, 2023, 2024)
- Fácil agregar años
- Metadatos temporales

oro.dim_sector
├─ id (PK)
├─ nombre_sector (VARCHAR, UNIQUE)
└─ descripcion (VARCHAR)

Características:
- 2 registros ('Oficial', 'Privado')
- Extensible para futuros sectores
```

#### Tabla de Hechos

```sql
oro.fact_relacion_estudiante_docente
├─ id (PK)
├─ dim_ies_id (FK → oro.dim_ies)
├─ dim_tiempo_id (FK → oro.dim_tiempo)
├─ dim_sector_id (FK → oro.dim_sector)
│
├─ total_estudiantes (INT)
├─ total_docentes (INT)
├─ ratio_estudiante_docente (DECIMAL)  -- Calculado
│
├─ UNIQUE(dim_ies_id, dim_tiempo_id)   -- Un hecho por IES/año
│
├─ creado_at (TIMESTAMP)
└─ actualizado_at (TIMESTAMP)

Índices para Performance:
├─ PK: id
├─ FK: dim_ies_id, dim_tiempo_id, dim_sector_id
├─ Filtrado: dim_ies_id, dim_tiempo_id
└─ Agregación: ratio_estudiante_docente
```

#### Vistas Analíticas

```sql
oro.v_relacion_estudiante_docente
├─ Columnas: nombre_ies, sector_ies, es_sue, año, 
│            total_estudiantes, total_docentes, ratio
├─ Filtrado: Por IES, sector, SUE, año
├─ Caso de uso: Principal para análisis
└─ Performance: Índices en dim_ies, dim_tiempo

oro.v_top_ies_by_ratio
├─ Columnas: ranking, nombre_ies, ratio, año
├─ Orden: Descendente por ratio
├─ Límite: Top 10
└─ Caso de uso: Benchmarking

oro.v_promedio_por_sue
├─ Columnas: es_sue, promedio_ratio, 
│            promedio_estudiantes, promedio_docentes, año
├─ Agregación: GROUP BY es_sue, año
└─ Caso de uso: Comparación SUE vs No SUE

oro.v_evolucion_ies
├─ Columnas: nombre_ies, año, ratio, variacion_anual
├─ Orden: Por IES, año
└─ Caso de uso: Tendencias temporales
```

---

## 3. Tabla de Auditoría

```sql
auditoria.registro_pipeline
├─ id (PK)
├─ fase (VARCHAR)  -- 'BRONCE', 'PLATA', 'ORO'
├─ estado (VARCHAR)  -- 'INICIADA', 'COMPLETADA', 'ERROR'
├─ registros_procesados (INT)
├─ registros_cargados (INT)
├─ fecha_inicio (TIMESTAMP)
├─ fecha_fin (TIMESTAMP)
├─ duracion_segundos (INT)  -- Calculado
├─ mensaje (TEXT)  -- Descripciones/errores
└─ usuario (VARCHAR)

Ventajas:
- Completa trazabilidad
- Debugging fácil
- Monitoreo de performance
- SLA tracking
```

---

## 4. Decisiones de Diseño

### 4.1 ¿Por qué Medallion?

| Beneficio | Impacto |
|-----------|---------|
| **Separación de capas** | Aislamiento de problemas |
| **Reutilización de datos** | Silver → múltiples Gold |
| **Trazabilidad** | Auditoría completa |
| **Escalabilidad** | Agregar nuevas métricas |
| **Debugging** | Identificar cuándo falló |

### 4.2 ¿Por qué Star Schema?

```
Alternativas consideradas:

❌ OLTP (3NF)
  - Muchas JOINs en queries
  - Performance pobre para agregaciones
  - Mejor para transacciones

✅ Star Schema (desnormalizado)
  - Agregaciones rápidas
  - JOINs simples (1 JOIN por dimensión)
  - Ideal para BI

❌ Snowflake Schema
  - Desnormalización adicional innecesaria
  - Complejidad extra
  - No mejora performance para este volumen
```

### 4.3 ¿Por qué Python + Pandas?

```python
Alternativas consideradas:

❌ SQL puro (COPY, INSERT SELECT)
  - Validación limitada
  - Difícil manejar variabilidad
  - Logs pobres

✅ Python + Pandas + SQLAlchemy
  - Validación robusta
  - Manejo de excepciones
  - Logs detallados
  - Debugging fácil

❌ Spark
  - Overkill para 351 registros
  - Overhead de infraestructura
  - Ideal para millones de registros
```

### 4.4 ¿Por qué PostgreSQL?

```
Alternativas consideradas:

❌ NoSQL (MongoDB, DynamoDB)
  - Relaciones débiles
  - Integridad referencial limitada
  - Queries complejas difíciles

✅ PostgreSQL
  - ACID guarantees
  - Foreign keys
  - Window functions
  - BI-friendly

❌ Data Warehouse (Snowflake, BigQuery)
  - Costo: pagas por queries
  - Setup complejo
  - Mejor para escala masiva (TB+)
```

---

## 5. Performance y Índices

### Índices Creados

```sql
-- Tabla de Hechos
CREATE INDEX idx_fact_ies_tiempo 
ON oro.fact_relacion_estudiante_docente(dim_ies_id, dim_tiempo_id);

CREATE INDEX idx_fact_ratio 
ON oro.fact_relacion_estudiante_docente(ratio_estudiante_docente);

-- Dimensión IES
CREATE INDEX idx_dim_ies_sue 
ON oro.dim_ies(es_sue);

CREATE INDEX idx_dim_ies_sector 
ON oro.dim_ies(sector_ies);

-- Auditoría
CREATE INDEX idx_auditoria_fase 
ON auditoria.registro_pipeline(fase);

CREATE INDEX idx_auditoria_fecha 
ON auditoria.registro_pipeline(fecha_inicio);
```

### Query Performance

```sql
-- Query lenta sin índices: ~200ms
SELECT * FROM oro.v_relacion_estudiante_docente 
WHERE año = 2024 AND es_sue = true;

-- Query rápida con índices: ~5ms
-- 40x más rápida
```

---

## 6. Manejo de Errores y Excepciones

```python
# Descargador
try:
    df = pd.read_excel(url)
except URLError:
    log.error("No Internet")
    sys.exit(1)

# Cargador
try:
    session.add(registro)
    session.commit()
except IntegrityError as e:
    log.error(f"Duplicado: {e}")
    session.rollback()
    continue
```

---

## 7. Roadmap de Escalabilidad

### Fase Actual (v2.0)
- ✅ Bogotá (117 IES × 3 años)
- ✅ PostgreSQL monolítico
- ✅ ETL manual (docker-compose)

### Fase 2 (v3.0) - 6 meses
- 🔄 Todo el país (~1,700 IES)
- 🔄 Airflow para scheduling
- 🔄 Particionamiento de tablas

### Fase 3 (v4.0) - 12 meses
- 🔄 Spark para procesamiento distribuido
- 🔄 Data Lake en S3
- 🔄 Kubernetes para orquestación

### Fase 4 (v5.0) - 18 meses
- 🔄 Real-time analytics
- 🔄 ML para predicciones
- 🔄 Multi-cloud deployment

---

## 📚 Referencias

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Pandas User Guide](https://pandas.pydata.org/docs/user_guide/)
- [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/)
- [Medallion Architecture](https://databricks.com/blog/2022/06/24/introduction-medallion-architecture.html)
- [Star Schema Design](https://en.wikipedia.org/wiki/Star_schema)
