/*
 * SNIES ANALYTICS - QUERIES PARA BI Y ANÁLISIS
 * Fase C: Accesibilidad y Backend
 *
 * Estas queries están listas para consumir desde:
 * - Tableau / Power BI / Metabase
 * - Python / R
 * - Herramientas de reporting
 *
 * Schema de datos: oro (Star Schema)
 * Tablas principales:
 *   oro.hecho_relacion_estudiante_docente  (tabla de hechos)
 *   oro.dim_ies                            (dimensión IES)
 *   oro.dim_tiempo                         (dimensión tiempo)
 */

-- =============================================================================
-- 1. RELACIÓN ESTUDIANTE/DOCENTE POR IES Y AÑO
-- =============================================================================

-- View principal (definida en schema.sql como oro.v_relacion_estudiante_docente)
SELECT * FROM oro.v_relacion_estudiante_docente
ORDER BY año DESC, nombre_ies ASC;

-- =============================================================================
-- 2. TOP 10 IES CON MAYOR RATIO (AÑOS CON MÁS ESTUDIANTES POR DOCENTE)
-- =============================================================================

SELECT
    año,
    posicion,
    nombre_ies,
    clasificacion_sue,
    sector_ies,
    total_estudiantes,
    total_docentes,
    estudiantes_por_docente
FROM oro.v_top_ies_by_ratio
WHERE posicion <= 10
ORDER BY año DESC, posicion ASC;

-- =============================================================================
-- 3. TOP 10 IES CON MENOR RATIO (MEJORES PROPORCIONES)
-- =============================================================================

SELECT
    nombre_ies,
    clasificacion_sue,
    sector_ies,
    año,
    total_estudiantes,
    total_docentes,
    estudiantes_por_docente,
    posicion_asc
FROM (
    SELECT
        d_ies.nombre_ies,
        CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
        d_ies.sector_ies,
        d_tiempo.año,
        f.total_estudiantes,
        f.total_docentes,
        f.estudiantes_por_docente,
        RANK() OVER (
            PARTITION BY d_tiempo.año
            ORDER BY f.estudiantes_por_docente ASC
        ) AS posicion_asc
    FROM oro.hecho_relacion_estudiante_docente f
    JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
    JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
    WHERE d_ies.esta_activo = TRUE
) ranked
WHERE posicion_asc <= 10
ORDER BY año DESC, posicion_asc ASC;

-- =============================================================================
-- 4. COMPARACIÓN SUE vs NO SUE (PROMEDIOS)
-- =============================================================================

SELECT * FROM oro.v_promedio_por_sue
ORDER BY año DESC;

-- =============================================================================
-- 5. EVOLUCIÓN DE UNA IES ESPECÍFICA
-- =============================================================================

-- Template: Reemplazar 'NACIONAL DE COLOMBIA' con nombre deseado
SELECT
    nombre_ies,
    año,
    total_estudiantes,
    total_docentes,
    estudiantes_por_docente,
    ratio_ano_anterior,
    CASE
        WHEN ratio_ano_anterior IS NULL THEN 'Año base'
        WHEN estudiantes_por_docente > ratio_ano_anterior THEN 'Aumentó'
        WHEN estudiantes_por_docente < ratio_ano_anterior THEN 'Disminuyó'
        ELSE 'Sin cambio'
    END AS tendencia
FROM oro.v_evolucion_ies
WHERE nombre_ies ILIKE '%NACIONAL DE COLOMBIA%'
ORDER BY año ASC;

-- =============================================================================
-- 6. ESTADÍSTICAS GENERALES POR AÑO
-- =============================================================================

SELECT
    d_tiempo.año,
    COUNT(DISTINCT d_ies.dim_ies_id)                                       AS cantidad_ies,
    COUNT(DISTINCT CASE WHEN d_ies.es_sue THEN d_ies.dim_ies_id END)       AS cantidad_sue,
    COUNT(DISTINCT CASE WHEN NOT d_ies.es_sue THEN d_ies.dim_ies_id END)   AS cantidad_no_sue,

    -- Totales
    SUM(f.total_estudiantes)                                                AS total_estudiantes,
    SUM(f.total_docentes)                                                   AS total_docentes,

    -- Promedios
    ROUND(AVG(f.total_estudiantes)::NUMERIC, 2)                            AS promedio_estudiantes_por_ies,
    ROUND(AVG(f.total_docentes)::NUMERIC, 2)                               AS promedio_docentes_por_ies,
    ROUND(AVG(f.estudiantes_por_docente)::NUMERIC, 2)                      AS promedio_ratio_global,

    -- Mínimos y Máximos
    MIN(f.estudiantes_por_docente)                                          AS ratio_minimo,
    MAX(f.estudiantes_por_docente)                                          AS ratio_maximo
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE
GROUP BY d_tiempo.año
ORDER BY d_tiempo.año DESC;

-- =============================================================================
-- 7. VARIACIÓN AÑO A AÑO (CRECIMIENTO/DECRECIMIENTO)
-- =============================================================================

WITH evolution AS (
    SELECT
        d_ies.nombre_ies,
        CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
        d_tiempo.año,
        f.total_estudiantes,
        f.total_docentes,
        f.estudiantes_por_docente,
        LAG(f.total_estudiantes) OVER (
            PARTITION BY d_ies.dim_ies_id ORDER BY d_tiempo.año
        ) AS est_ano_anterior,
        LAG(f.total_docentes) OVER (
            PARTITION BY d_ies.dim_ies_id ORDER BY d_tiempo.año
        ) AS doc_ano_anterior
    FROM oro.hecho_relacion_estudiante_docente f
    JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
    JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
    WHERE d_ies.esta_activo = TRUE
)
SELECT
    nombre_ies,
    clasificacion_sue,
    año,
    total_estudiantes,
    total_docentes,
    estudiantes_por_docente,

    CASE
        WHEN est_ano_anterior IS NULL THEN NULL
        ELSE (total_estudiantes - est_ano_anterior)
    END AS delta_estudiantes,

    CASE
        WHEN est_ano_anterior IS NULL THEN NULL
        ELSE ROUND(
            ((total_estudiantes - est_ano_anterior)::DECIMAL / NULLIF(est_ano_anterior, 0) * 100),
            2
        )
    END AS pct_cambio_estudiantes,

    CASE
        WHEN doc_ano_anterior IS NULL THEN NULL
        ELSE (total_docentes - doc_ano_anterior)
    END AS delta_docentes
FROM evolution
WHERE año > 2022
ORDER BY año DESC, nombre_ies ASC;

-- =============================================================================
-- 8. IES CON MEJOR CAPACIDAD (MÁS ESTUDIANTES, MENOS DOCENTES)
-- =============================================================================

SELECT
    d_ies.nombre_ies,
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_tiempo.año,
    f.total_estudiantes,
    f.total_docentes,
    f.estudiantes_por_docente,
    RANK() OVER (
        PARTITION BY d_tiempo.año ORDER BY f.estudiantes_por_docente DESC
    ) AS rank_efficiency
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE
    AND f.estudiantes_por_docente IS NOT NULL
    AND f.total_estudiantes > 0
ORDER BY d_tiempo.año DESC, rank_efficiency ASC
LIMIT 20;

-- =============================================================================
-- 9. REPORTE EJECUTIVO: RESUMEN POR CLASIFICACIÓN SUE
-- =============================================================================

SELECT
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_tiempo.año,

    COUNT(DISTINCT d_ies.dim_ies_id)                                                      AS num_instituciones,

    SUM(f.total_estudiantes)                                                               AS total_estudiantes,
    ROUND(AVG(f.total_estudiantes)::NUMERIC, 0)                                            AS promedio_estudiantes,

    SUM(f.total_docentes)                                                                  AS total_docentes,
    ROUND(AVG(f.total_docentes)::NUMERIC, 0)                                               AS promedio_docentes,

    ROUND(
        (SUM(f.total_estudiantes)::DECIMAL / NULLIF(SUM(f.total_docentes), 0)),
        2
    )                                                                                      AS ratio_global,
    ROUND(AVG(f.estudiantes_por_docente)::NUMERIC, 2)                                      AS promedio_ratio
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE
GROUP BY d_ies.es_sue, d_tiempo.año
ORDER BY d_tiempo.año DESC, d_ies.es_sue;

-- =============================================================================
-- 10. EXPORTACIÓN: FORMATO PARA EXCEL/CSV
-- =============================================================================

SELECT
    d_ies.nombre_ies          AS "Institución",
    d_ies.sector_ies          AS "Sector",
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS "Clasificación",
    d_tiempo.año              AS "Año",
    f.total_estudiantes       AS "Total Estudiantes",
    f.total_docentes          AS "Total Docentes",
    f.estudiantes_por_docente AS "Estudiantes por Docente"
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE
ORDER BY d_tiempo.año DESC, d_ies.nombre_ies ASC;

-- =============================================================================
-- AUDITORÍA: VER LOGS DEL PIPELINE
-- =============================================================================

SELECT * FROM auditoria.registro_pipeline
ORDER BY creado_at DESC
LIMIT 20;
