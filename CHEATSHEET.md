# SNIES Analytics — Cheat Sheet

## ARRANCAR EL PROYECTO

```bash
# Primera vez (descarga imágenes + corre pipeline completo ~3 min)
docker compose up --build

# Veces siguientes — solo servicios, datos ya están
docker compose up postgres metabase pgadmin

# Pipeline completo otra vez (re-descarga datos del SNIES)
docker compose up
```

## APAGAR

```bash
docker compose down          # apaga, conserva datos
docker compose down -v       # apaga y borra todo (reinicio limpio)
```

## VER QUÉ ESTÁ CORRIENDO

```bash
docker ps                    # contenedores activos
docker compose logs -f etl   # logs del ETL en vivo
docker compose logs -f       # logs de todo
```

---

## ACCEDER A LAS HERRAMIENTAS

| Herramienta | Dónde | Usuario | Contraseña |
|---|---|---|---|
| Metabase (BI) | http://localhost:3000 | el que creaste | el que creaste |
| PgAdmin web | http://localhost:5050 | admin@pgadmin.com | admin |
| PostgreSQL desktop | localhost **5433** | postgres | postgres |
| PostgreSQL desde Docker | host: `postgres` puerto: `5432` | postgres | postgres |

---

## POSTGRESQL — COMANDOS ÚTILES

```bash
# Entrar a la BD desde terminal
docker exec -it snies_postgres psql -U postgres -d snies_analytics

# Verificar que los datos están bien
docker exec -it snies_postgres psql -U postgres -d snies_analytics -c \
  "SELECT COUNT(*) FROM oro.hecho_relacion_estudiante_docente;"
# Debe retornar: 351
```

---

## QUERIES PARA LA DEMO

```sql
-- 1. Ver todas las IES con su ratio (vista principal)
SELECT * FROM oro.v_relacion_estudiante_docente
WHERE año = 2024
ORDER BY estudiantes_por_docente DESC;

-- 2. Top 10 con más estudiantes por docente
SELECT * FROM oro.v_top_ies_by_ratio
WHERE posicion <= 10 AND año = 2024
ORDER BY posicion;

-- 3. Top 10 con mejor proporción (menor ratio)
SELECT nombre_ies, año, total_estudiantes, total_docentes, estudiantes_por_docente
FROM oro.v_relacion_estudiante_docente
WHERE año = 2024 AND estudiantes_por_docente IS NOT NULL
ORDER BY estudiantes_por_docente ASC
LIMIT 10;

-- 4. SUE vs No SUE (comparativa)
SELECT * FROM oro.v_promedio_por_sue
ORDER BY año DESC;

-- 5. Evolución de una universidad específica
SELECT * FROM oro.v_evolucion_ies
WHERE nombre_ies ILIKE '%NACIONAL%'
ORDER BY año;

-- 6. Estadísticas generales por año
SELECT
    d_tiempo.año,
    COUNT(DISTINCT d_ies.dim_ies_id) AS cantidad_ies,
    SUM(f.total_estudiantes) AS total_estudiantes,
    SUM(f.total_docentes) AS total_docentes,
    ROUND(AVG(f.estudiantes_por_docente)::NUMERIC, 2) AS promedio_ratio
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE
GROUP BY d_tiempo.año
ORDER BY d_tiempo.año DESC;

-- 7. Ver logs del pipeline (auditoría)
SELECT etapa, estado, mensaje, registros_afectados, creado_at
FROM auditoria.registro_pipeline
ORDER BY creado_at;

-- 8. Conteo de todas las tablas (verificación rápida)
SELECT 'bronce.snies_crudo' AS tabla, COUNT(*) FROM bronce.snies_crudo
UNION ALL SELECT 'plata.snies_ies', COUNT(*) FROM plata.snies_ies
UNION ALL SELECT 'oro.dim_ies', COUNT(*) FROM oro.dim_ies
UNION ALL SELECT 'oro.hecho_relacion_estudiante_docente', COUNT(*) FROM oro.hecho_relacion_estudiante_docente;
```

---

## EXTRAER ARCHIVOS DEL CONTENEDOR

```bash
# Copiar CSV y Excel descargados a tu carpeta local
docker cp snies_etl:/app/data/. "e:/GitHub/SNIES Analytics/snies-analytics/data/"
```

---

## GIT

```bash
git status                   # ver qué cambió
git log --oneline -5         # últimos 5 commits
git push origin main         # subir a GitHub
```

---

## SI ALGO FALLA

```bash
# Ver el error
docker compose logs etl

# Reinicio limpio (último recurso)
docker compose down -v
docker compose up --build

# Verificar que PostgreSQL está sano
docker exec snies_postgres pg_isready -U postgres
```
