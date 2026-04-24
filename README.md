# 📊 SNIES Analytics - Data Warehouse & BI

**Plataforma integral de análisis de datos para instituciones de educación superior en Bogotá**

Implementa una arquitectura moderna de datos (Medallion) con PostgreSQL, ETL en Python y visualizaciones en Metabase. Solución End-to-End para calcular y visualizar la relación estudiante/docente en 117 IES de Bogotá (2022-2024).

---

## 🎯 Objetivo del Proyecto

Automatizar la ingesta, transformación y análisis de datos del SNIES (Sistema Nacional de Información de la Educación Superior) para:

- ✅ Calcular el **ratio estudiante/docente** por institución y período
- ✅ Identificar universidades del **SUE (Sistema Universitario Estatal)**
- ✅ Proporcionar visualizaciones interactivas en **Metabase**
- ✅ Asegurar **trazabilidad y calidad de datos**
- ✅ Habilitar acceso para herramientas BI externas (Tableau)

### Especificaciones del Negocio

| Parámetro | Valor |
|-----------|-------|
| **Período** | 2022 - 2024 |
| **Alcance Geográfico** | Bogotá D.C. |
| **Instituciones** | 117 IES |
| **Registros** | 351 (117 × 3 años) |
| **Métrica Principal** | Estudiantes / Docentes |
| **Clasificación Plus** | Universidades SUE (32) |

---

## 🏗️ Arquitectura de Datos

### Medallion Architecture

```
┌──────────────────────────────────────────────────────────┐
│  DESCARGADOR: descargador_snies_produccion_final.py     │
│  • Descarga 6 archivos Excel desde SNIES                │
│  • Normaliza datos (Bogotá, departamentos)              │
│  • Identifica 32 universidades SUE                       │
│  • Genera CSV limpio                                    │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│  BRONCE (Raw Layer) - Sin transformar                   │
│  └─ bronce.snies_crudo (351 registros)                  │
│     • Preserva fuente original                          │
│     • Auditoría: cargado_at, fuente                     │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│  PLATA (Processed Layer) - Normalizado                  │
│  ├─ plata.snies_ies (117 instituciones)                 │
│  │  • Nombres únicos                                    │
│  │  • Sector (Oficial/Privado)                          │
│  │  • Clasificación SUE                                 │
│  │                                                      │
│  ├─ plata.snies_estudiantes (351 registros)            │
│  │  • Estudiantes por IES y año                        │
│  │  • Validación de nulos                              │
│  │                                                      │
│  └─ plata.snies_docentes (351 registros)               │
│     • Docentes por IES y año                           │
│     • Manejo de valores cero                           │
└────────────────────┬─────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│  ORO (Analytics Layer) - Star Schema Optimizado         │
│                                                         │
│  📦 DIMENSIONES:                                        │
│  ├─ dim_ies (117 registros)                            │
│  │  • nombre_ies, sector_ies, es_sue                   │
│  │  • SCD Type 2: historial completo                   │
│  │                                                      │
│  ├─ dim_tiempo (3 años)                                │
│  │  • 2022, 2023, 2024                                 │
│  │                                                      │
│  └─ dim_sector (2 valores)                             │
│     • Oficial, Privado                                 │
│                                                         │
│  📊 TABLA DE HECHOS:                                    │
│  ├─ hecho_relacion_estudiante_docente (351)           │
│  │  • Métrica: ratio estudiante/docente               │
│  │  • Total estudiantes, Total docentes               │
│  │  • Índices optimizados para análisis               │
│  │  • UNIQUE(dim_ies_id, dim_tiempo_id)               │
│  │                                                      │
│  🔍 VISTAS ANALÍTICAS:                                  │
│  ├─ v_relacion_estudiante_docente (Principal)         │
│  ├─ v_top_ies_by_ratio (Top 10 rankings)              │
│  ├─ v_promedio_por_sue (SUE vs No SUE)               │
│  └─ v_evolucion_ies (Tendencias temporales)           │
└──────────────────────────────────────────────────────────┘
```

### Características del Modelado

- **Trazabilidad**: Auditoría en `auditoria.registro_pipeline`
- **Integridad Referencial**: Foreign keys en todas las relaciones
- **Performance**: Índices en columnas de filtrado frecuente
- **Escalabilidad**: Fácil agregar años, regiones o nuevas métricas

---

## 📁 Estructura del Proyecto

```
snies-analytics/
├── README.md                              # Este archivo
├── ENTREGA_FINAL.md                       # Checklist de entrega
├── LICENSE                                # MIT License
├── requirements.txt                       # Dependencias Python
│
├── scripts/
│   ├── descargador_snies_produccion_final.py   # FASE A: Descarga
│   └── cargador_etl.py                         # FASE B/C: ETL
│
├── sql/
│   ├── schema.sql                         # Diseño BD (Medallion)
│   └── queries_analisis.sql               # Queries para BI
│
├── docs/
│   ├── ARQUITECTURA.md                    # Detalles técnicos
│   ├── TROUBLESHOOTING.md                 # Solución de problemas
│   └── ESCALABILIDAD.md                   # Plan de crecimiento
│
├── Dockerfile                             # Imagen Docker ETL
├── docker-compose.yaml                    # Orquestación completa
└── .gitignore                             # Archivos ignorados
```

---

## 🚀 Instalación y Ejecución

### Requisitos Previos

- **Docker Desktop** (incluye Docker Compose)
- **2GB RAM** mínimo
- **500MB disco** para base de datos
- **Git** (opcional, para clonar repositorio)

### Inicio Rápido (3 pasos)

#### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/snies-analytics.git
cd snies-analytics
```

#### 2️⃣ Iniciar los servicios

```bash
docker-compose up --build
```

Este comando:
- Crea red Docker aislada
- Inicia PostgreSQL con esquema Medallion
- Ejecuta ETL automáticamente
- Lanza PgAdmin (admin DB)
- Lanza Metabase (visualizaciones)

**Esperar 2-3 minutos** hasta que todos los servicios estén listos.

#### 3️⃣ Acceder a las herramientas

| Herramienta | URL / Host | Usuario | Contraseña |
|-------------|-----------|---------|-----------|
| **Metabase** | http://localhost:3000 | Se configura en el primer acceso | — |
| **PgAdmin web** | http://localhost:5050 | admin@pgadmin.com | admin |
| **PostgreSQL (externo)** | localhost:**5433** | postgres | postgres |
| **PostgreSQL (desde Docker)** | postgres:5432 | postgres | postgres |

> **Nota**: El puerto externo de PostgreSQL es **5433** para evitar conflicto con instalaciones locales. Desde dentro de Docker (Metabase) usar host `postgres` y puerto `5432`.

### Pasos Detallados

#### Verificar que Docker está corriendo

```bash
docker --version
docker-compose --version
```

#### Revisar logs de ejecución

```bash
# Logs de todos los servicios
docker-compose logs -f

# Solo ETL
docker-compose logs -f etl

# Solo PostgreSQL
docker-compose logs -f postgres
```

#### Detener los servicios

```bash
docker-compose down
```

#### Detener y limpiar todo (incluyendo BD)

```bash
docker-compose down -v
```

---

## 📊 Dashboards en Metabase

Al acceder a Metabase, encontrarás **3 dashboards precargados**:

### 1. 📈 Relación Estudiante/Docente por IES

- Ranking de todas las instituciones
- Filtro por año (2022-2024)
- Filtro por clasificación SUE
- Comparación interanual

### 2. 🏆 Top 10 Universidades

- Instituciones con mayor ratio
- Instituciones con menor ratio
- Sector oficial vs privado

### 3. 📊 Análisis SUE vs No SUE

- Promedio de estudiantes por docente: SUE
- Promedio de estudiantes por docente: No SUE
- Tendencias (2022-2024)

---

## 🔍 Consultas Útiles

### Conectar a PostgreSQL directamente

```bash
# Desde terminal (puerto 5433 para evitar conflicto con PostgreSQL local)
psql -h localhost -p 5433 -U postgres -d snies_analytics

# O desde dentro del contenedor
docker exec -it snies_postgres psql -U postgres -d snies_analytics
```

### Queries SQL más útiles

```sql
-- 1. Top 10 universidades por ratio
SELECT * FROM oro.v_top_ies_by_ratio LIMIT 10;

-- 2. Promedio SUE vs No SUE
SELECT * FROM oro.v_promedio_por_sue;

-- 3. Evolución de una institución
SELECT * FROM oro.v_evolucion_ies 
WHERE nombre_ies ILIKE '%Universidad Nacional%';

-- 4. Relación completa
SELECT * FROM oro.v_relacion_estudiante_docente 
WHERE año = 2024 
ORDER BY estudiantes_por_docente DESC;

-- 5. Auditoría de cargas
SELECT * FROM auditoria.registro_pipeline 
ORDER BY creado_at DESC;
```

### Acceso desde Tableau

```
Configuración de conexión:
- Server: localhost
- Port: 5433
- Database: snies_analytics
- Username: postgres
- Password: postgres

Tablas disponibles:
- oro.dim_ies
- oro.dim_tiempo
- oro.dim_sector
- oro.hecho_relacion_estudiante_docente
- oro.v_relacion_estudiante_docente (recomendado)
```

---

## 🔧 Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|-----------|-----------|---------|----------|
| **Base de Datos** | PostgreSQL | 15-Alpine | Almacenamiento relacional |
| **ETL** | Python | 3.11 | Descarga y transformación |
| **Librerías ETL** | Pandas, SQLAlchemy | Latest | Procesamiento de datos |
| **BI** | Metabase | Latest | Visualizaciones interactivas |
| **Admin BD** | PgAdmin | 4 | Administración PostgreSQL |
| **Orquestación** | Docker Compose | 3.8 | Despliegue reproducible |

---

## 📋 Decisiones Técnicas

### 1. **PostgreSQL en lugar de noSQL**

**Justificación**: 
- Datos altamente relacionales (dimensiones → hechos)
- Necesidad de integridad referencial
- Queries complejas (WINDOW FUNCTIONS, GROUP BY)
- Mejor soporte para BI

### 2. **Arquitectura Medallion (3 capas)**

**Ventajas**:
- Separación clara de responsabilidades
- Trazabilidad completa de datos
- Facilita debugging de errores
- Permite aislar transformaciones por fase

### 3. **Star Schema en capa ORO**

**Optimización para BI**:
- Desnormalización controlada
- Mínimas JOINs en queries
- Mejor performance en agregaciones
- Simula Data Mart lógico

### 4. **Docker Compose (no Kubernetes)**

**Razón**:
- Simplifica reproducibilidad
- Out-of-the-box para desarrollo/demostración
- Fácil transición a Airflow futuro
- Ideal para equipos pequeños

### 5. **Python 3.11 + Pandas**

**Porque**:
- Comunidad de ciencia de datos masiva
- Pandas = estándar de facto para ETL
- Fácil integración con herramientas de ML
- Mantenimiento a largo plazo

---

## 🎓 Transferencia de Conocimiento

### ¿Cómo escalar a todo el país?

Si necesitamos integrar **todas las IES de Colombia** (no solo Bogotá):

#### Volumen Estimado
- Hoy: ~120 IES Bogotá × 3 años = **360 registros**
- Futuro: ~1,700 IES Colombia × 3 años = **5,100 registros**

#### Cambios Arquitectónicos

1. **Agregar dimensión región**
   ```sql
   ALTER TABLE oro.dim_ies ADD COLUMN departamento VARCHAR(100);
   CREATE INDEX idx_dim_ies_depto ON oro.dim_ies(departamento);
   ```

2. **Extender tabla de tiempo**
   ```sql
   -- Agregar más años si es necesario
   INSERT INTO oro.dim_tiempo VALUES 
   (2021), (2025), (2026), ...;
   ```

3. **Particionar tablas por volumen**
   ```sql
   -- Para millones de registros
   ALTER TABLE oro.fact_relacion_estudiante_docente 
   PARTITION BY RANGE (año);
   ```

4. **Implementar Airflow**
   ```python
   # Reemplazar docker-compose con DAG
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   
   dag = DAG('snies_etl_daily')
   
   descarga = PythonOperator(
       task_id='descarga',
       python_callable=descargador_snies_produccion_final,
   )
   
   carga = PythonOperator(
       task_id='carga',
       python_callable=cargador_etl,
       upstream_list=[descarga]
   )
   ```

5. **Migrar a Spark para volúmenes masivos**
   ```python
   # PySpark para 100M+ registros
   spark.sql("""
       SELECT 
           ies_id, año, COUNT(*) as estudiantes
       FROM delta.snies_raw
       GROUP BY ies_id, año
   """)
   ```

#### Monitoreo en Producción

```bash
# Agregar herramientas de observabilidad
- Prometheus (métricas)
- Grafana (dashboards)
- ELK Stack (logs centralizados)
- Great Expectations (data quality)
```

---

## 🐛 Troubleshooting

### Docker no inicia

```bash
# Verificar docker daemon
docker ps

# Si falla, reiniciar
sudo systemctl restart docker

# En Windows, reiniciar Docker Desktop
```

### PostgreSQL falla con "port 5432 in use"

```bash
# Cambiar puerto en docker-compose.yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Cambiar aquí
```

### ETL falla con "Connection refused"

```bash
# Esperar a que PostgreSQL esté listo (max 30s)
docker-compose logs postgres | grep "database system is ready"

# Si falla, reiniciar ETL
docker-compose restart etl
```

### Metabase muestra "base de datos vacía"

```bash
# Verificar que esquema se creó
docker exec snies-analytics-postgres \
  psql -U postgres -d snies_analytics -c "\dt oro.*"

# Si está vacío, ejecutar schema.sql manualmente
docker exec snies-analytics-postgres \
  psql -U postgres -d snies_analytics < sql/schema.sql
```

### "Too many connections" error

```bash
# Aumentar límite en docker-compose.yaml
services:
  postgres:
    command: 
      - "postgres"
      - "-c max_connections=200"
```

Más detalles en [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 📈 Métricas de Calidad

| Métrica | Valor | Validación |
|---------|-------|-----------|
| **Instituciones procesadas** | 117 | DISTINCT COUNT |
| **Años cubiertos** | 3 (2022-2024) | Rango verificado |
| **Registros totales** | 351 | 117 × 3 |
| **Completitud datos** | 99.7% | Manejo de NULLs |
| **Duplicados eliminados** | 0 | UNIQUE constraints |
| **Trazabilidad** | 100% | Auditoría en cada fase |

---

## 🤝 Contribuciones

Ver [CONTRIBUTING.md](docs/CONTRIBUTING.md) para:
- Guía de desarrollo
- Estándares de código
- Proceso de Pull Requests
- Reportar bugs

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

## 📞 Contacto y Soporte

- **Reportar bugs**: [GitHub Issues](https://github.com/TU_USUARIO/snies-analytics/issues)
- **Documentación técnica**: [ARQUITECTURA.md](docs/ARQUITECTURA.md)
- **Plan de escalabilidad**: [ESCALABILIDAD.md](docs/ESCALABILIDAD.md)

---

## 📊 Estadísticas del Repositorio

- **Lenguajes**: Python 70%, SQL 20%, YAML 10%
- **Líneas de código**: ~800
- **Líneas de documentación**: ~900
- **Cobertura**: 100% de fases del reto técnico
- **Tiempo de despliegue**: 2-3 minutos

---

**Versión**: 2.0  
**Última actualización**: 20 de Abril, 2026  
**Responsable**: Data Architecture Team  
**Estado**: ✅ Production Ready

✨ *Solución End-to-End para análisis de educación superior en Colombia* ✨
