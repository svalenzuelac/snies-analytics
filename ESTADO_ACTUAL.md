# Estado Actual del Repositorio — SNIES Analytics

**Fecha última actualización**: 24 de Abril, 2026  
**Estado**: PRODUCTION READY — pipeline probado end-to-end con Docker  
**Versión**: 4.0

---

## Resultado de la prueba completa (24-abril-2026)

Pipeline ejecutado exitosamente con `docker compose up --build`:

```
FASE 1 — Descarga
  6 archivos Excel descargados del portal SNIES (~42 MB)
  117 IES únicas de Bogotá identificadas
  CSV generado: /app/data/snies_relacion_estudiante_docente.csv

FASE 2 — ETL Medallion
  bronce.snies_crudo                   → 351 registros
  plata.snies_ies                      → 117 IES
  plata.snies_estudiantes              → 351 registros
  plata.snies_docentes                 → 351 registros
  oro.dim_ies                          → 117 dimensiones
  oro.dim_tiempo                       → 3 años (2022, 2023, 2024)
  oro.hecho_relacion_estudiante_docente → 351 hechos
  auditoria.registro_pipeline          → 3 logs

Estado: EXITO — sin errores
```

---

## Cómo correr el proyecto

### Requisitos
- Docker Desktop instalado y corriendo

### Comando único

```bash
git clone https://github.com/svalenzuelac/snies-analytics.git
cd snies-analytics
docker compose up --build
```

Esperar ~3 minutos. Cuando aparezca `snies_etl | COMPLETADO` el sistema está listo.

### Acceso a herramientas

| Herramienta | URL / Host | Usuario | Contraseña |
|---|---|---|---|
| Metabase (BI) | http://localhost:3000 | Configurar en primer acceso | — |
| PgAdmin web | http://localhost:5050 | admin@pgadmin.com | admin |
| PostgreSQL externo | localhost:**5433** | postgres | postgres |
| PostgreSQL desde Docker | postgres:5432 | postgres | postgres |

> El puerto externo es **5433** (no 5432) para evitar conflicto con PostgreSQL local instalado en Windows.

### Conectar PgAdmin desktop a Docker

- Host: `127.0.0.1`
- Port: `5433`
- Database: `snies_analytics`
- Username: `postgres`
- Password: `postgres`

### Conectar Metabase a PostgreSQL

- Host: `postgres` *(nombre del contenedor, no localhost)*
- Port: `5432`
- Database: `snies_analytics`
- Username: `postgres`
- Password: `postgres`

### Verificar datos

```bash
docker exec -it snies_postgres psql -U postgres -d snies_analytics -c \
  "SELECT COUNT(*) FROM oro.hecho_relacion_estudiante_docente;"
# Resultado esperado: 351

docker exec -it snies_postgres psql -U postgres -d snies_analytics -c \
  "SELECT * FROM auditoria.registro_pipeline ORDER BY creado_at;"
# Muestra logs de cada fase: bronce, plata, oro
```

### Extraer archivos Excel del contenedor

```bash
docker cp snies_etl:/app/data/. ./data/
```

### Apagar

```bash
docker compose down        # conserva datos
docker compose down -v     # borra datos (reinicio limpio)
```

---

## Arquitectura de datos

```
Portal SNIES (6 archivos Excel)
         ↓ descargador_snies_produccion_final.py
data/snies_relacion_estudiante_docente.csv  (351 filas, 117 IES × 3 años)
         ↓ cargador_etl.py
BRONCE: bronce.snies_crudo                 (351 registros raw)
         ↓
PLATA:  plata.snies_ies                    (117 IES normalizadas)
        plata.snies_estudiantes             (351 registros)
        plata.snies_docentes               (351 registros)
         ↓
ORO:    oro.dim_ies                        (117 — dimensión IES)
        oro.dim_tiempo                     (3 — años 2022, 2023, 2024)
        oro.dim_sector                     (Oficial, Privado, Desconocido)
        oro.hecho_relacion_estudiante_docente  (351 hechos + ratio calculado)
         ↓
VISTAS: oro.v_relacion_estudiante_docente  (vista principal con rankings)
        oro.v_promedio_por_sue             (comparativa SUE vs No SUE)
        oro.v_top_ies_by_ratio             (top por año, descendente)
        oro.v_evolucion_ies                (evolución con LAG por IES)
         ↓
Metabase / PgAdmin / Tableau / Power BI
```

---

## Bugs corregidos (sesiones 23-24 abril 2026)

| # | Archivo | Problema | Fix |
|---|---|---|---|
| 1 | `cargador_etl.py` | BD default `snies_analisis` | → `snies_analytics` |
| 2 | `queries_analisis.sql` | Schema `gold.` (26 ocurrencias) | → `oro.` |
| 3 | `queries_analisis.sql` | Tabla `fact_relacion_...` | → `hecho_relacion_...` |
| 4 | `queries_analisis.sql` | Columnas `is_active`, `year`, `ies_name` | → `esta_activo`, `año`, `nombre_ies` |
| 5 | `queries_analisis.sql` | `audit.pipeline_log` | → `auditoria.registro_pipeline` |
| 6 | `queries_analisis.sql` | `RANK()` en cláusula `WHERE` (SQL inválido) | Reescrito como subquery |
| 7 | `schema.sql` | Vistas `v_top_ies_by_ratio` y `v_evolucion_ies` no existían | Agregadas |
| 8 | Ambos scripts | Rutas relativas al CWD | Ancladas con `Path(__file__)` |
| 9 | Ambos scripts | `subprocess.check_call` auto-install | Eliminado |
| 10 | `descargador_snies_produccion_final.py` | `shutil.rmtree()` borra punto de montaje Docker | Reemplazado por borrado de archivos individuales |
| 11 | `docker-compose.yaml` | `- .:/app` causaba `PermissionError` al escribir CSV | Separado en 3 volúmenes específicos |
| 12 | `docker-compose.yaml` | Puerto 5432 conflicta con PostgreSQL local | Cambiado a 5433 externo |

---

## Estructura del proyecto

```
snies-analytics/
├── scripts/
│   ├── descargador_snies_produccion_final.py   ← Fase A: descarga SNIES
│   └── cargador_etl.py                          ← Fases B/C: ETL Medallion
├── sql/
│   ├── schema.sql                               ← 4 schemas, 4 tablas oro, 4 vistas
│   ├── queries_analisis.sql                     ← 10 queries para BI
│   └── init-metabase.sql                        ← Crea BD para Metabase
├── docs/
│   ├── ARQUITECTURA.md
│   ├── CONTRIBUTING.md
│   ├── ESCALABILIDAD.md
│   └── TROUBLESHOOTING.md
├── data/                                        ← Ignorado por git (.gitignore)
├── README.md
├── ESTADO_ACTUAL.md                             ← Este archivo
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt
```
