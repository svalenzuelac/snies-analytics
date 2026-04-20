/*
 * SNIES ANALYTICS - QUERIES PARA BI Y ANÁLISIS
 * Fase C: Accesibilidad y Backend
 * 
 * Estas queries están listas para consumir desde:
 * - Tableau / Power BI
 * - Python / R
 * - Herramientas de reporting
 */

-- =============================================================================
-- 1. RELACIÓN ESTUDIANTE/DOCENTE POR IES Y AÑO
-- =============================================================================

-- View principal (ya existe en schema.sql)
-- Visualizar todas las IES con su ratio por año
SELECT * FROM gold.v_relacion_estudiante_docente
ORDER BY year DESC, ies_name ASC;

-- =============================================================================
-- 2. TOP 10 IES CON MAYOR RATIO (AÑOS CON MÁS ESTUDIANTES POR DOCENTE)
-- =============================================================================

SELECT 
    year,
    posicion,
    ies_name,
    clasificacion_sue,
    sector_ies,
    total_estudiantes,
    total_docentes,
    estudiantes_por_docente
FROM gold.v_top_ies_by_ratio
ORDER BY year DESC, posicion ASC;

-- =============================================================================
-- 3. TOP 10 IES CON MENOR RATIO (MEJORES PROPORCIONES)
-- =============================================================================

SELECT 
    d_ies.ies_name,
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_ies.sector_ies,
    d_tiempo.year,
    f.total_estudiantes,
    f.total_docentes,
    f.estudiantes_por_docente,
    RANK() OVER (PARTITION BY d_tiempo.year ORDER BY f.estudiantes_por_docente ASC) AS posicion
FROM gold.fact_relacion_estudiante_docente f
JOIN gold.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN gold.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.is_active = TRUE
    AND RANK() OVER (PARTITION BY d_tiempo.year ORDER BY f.estudiantes_por_docente ASC) <= 10
ORDER BY d_tiempo.year DESC, posicion ASC;

-- =============================================================================
-- 4. COMPARACIÓN SUE vs NO SUE (PROMEDIOS)
-- =============================================================================

SELECT * FROM gold.v_promedio_por_sue
ORDER BY year DESC;

-- =============================================================================
-- 5. EVOLUCIÓN DE UNA IES ESPECÍFICA
-- =============================================================================

-- Template: Reemplazar 'UNIVERSIDAD NACIONAL DE COLOMBIA' con nombre deseado
SELECT 
    ies_name,
    year,
    total_estudiantes,
    total_docentes,
    estudiantes_por_docente,
    CASE 
        WHEN estudiantes_por_docente > LAG(estudiantes_por_docente) 
             OVER (ORDER BY year) 
        THEN 'Aumentó'
        WHEN estudiantes_por_docente < LAG(estudiantes_por_docente) 
             OVER (ORDER BY year) 
        THEN 'Disminuyó'
        ELSE 'Sin cambio'
    END AS tendencia
FROM gold.v_evolucion_ies
WHERE ies_name ILIKE '%NACIONAL DE COLOMBIA%'
ORDER BY year ASC;

-- =============================================================================
-- 6. ESTADÍSTICAS GENERALES POR AÑO
-- =============================================================================

SELECT 
    d_tiempo.year,
    COUNT(DISTINCT d_ies.dim_ies_id) AS cantidad_ies,
    COUNT(DISTINCT CASE WHEN d_ies.es_sue THEN d_ies.dim_ies_id END) AS cantidad_sue,
    COUNT(DISTINCT CASE WHEN NOT d_ies.es_sue THEN d_ies.dim_ies_id END) AS cantidad_no_sue,
    
    -- Totales
    SUM(f.total_estudiantes) AS total_estudiantes,
    SUM(f.total_docentes) AS total_docentes,
    
    -- Promedios
    ROUND(AVG(f.total_estudiantes)::NUMERIC, 2) AS promedio_estudiantes_por_ies,
    ROUND(AVG(f.total_docentes)::NUMERIC, 2) AS promedio_docentes_por_ies,
    ROUND(AVG(f.estudiantes_por_docente)::NUMERIC, 2) AS promedio_ratio_global,
    
    -- Mínimos y Máximos
    MIN(f.estudiantes_por_docente) AS ratio_minimo,
    MAX(f.estudiantes_por_docente) AS ratio_maximo
FROM gold.fact_relacion_estudiante_docente f
JOIN gold.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN gold.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.is_active = TRUE
GROUP BY d_tiempo.year
ORDER BY d_tiempo.year DESC;

-- =============================================================================
-- 7. VARIACIÓN AÑO A AÑO (CRECIMIENTO/DECRECIMIENTO)
-- =============================================================================

WITH evolution AS (
    SELECT 
        d_ies.ies_name,
        CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
        d_tiempo.year,
        f.total_estudiantes,
        f.total_docentes,
        f.estudiantes_por_docente,
        LAG(f.total_estudiantes) OVER (PARTITION BY d_ies.dim_ies_id ORDER BY d_tiempo.year) AS est_ano_anterior,
        LAG(f.total_docentes) OVER (PARTITION BY d_ies.dim_ies_id ORDER BY d_tiempo.year) AS doc_ano_anterior
    FROM gold.fact_relacion_estudiante_docente f
    JOIN gold.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
    JOIN gold.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
    WHERE d_ies.is_active = TRUE
)
SELECT 
    ies_name,
    clasificacion_sue,
    year,
    total_estudiantes,
    total_docentes,
    estudiantes_por_docente,
    
    -- Variaciones
    CASE 
        WHEN est_ano_anterior IS NULL THEN NULL
        ELSE (total_estudiantes - est_ano_anterior)
    END AS delta_estudiantes,
    
    CASE 
        WHEN est_ano_anterior IS NULL THEN NULL
        ELSE ROUND(((total_estudiantes - est_ano_anterior)::DECIMAL / est_ano_anterior * 100), 2)
    END AS pct_cambio_estudiantes,
    
    CASE 
        WHEN doc_ano_anterior IS NULL THEN NULL
        ELSE (total_docentes - doc_ano_anterior)
    END AS delta_docentes
FROM evolution
WHERE year > 2022  -- Solo años con comparación
ORDER BY year DESC, ies_name ASC;

-- =============================================================================
-- 8. IES CON MEJOR CAPACIDAD (MÁS ESTUDIANTES, MENOS DOCENTES)
-- =============================================================================

SELECT 
    d_ies.ies_name,
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_tiempo.year,
    f.total_estudiantes,
    f.total_docentes,
    f.estudiantes_por_docente,
    RANK() OVER (PARTITION BY d_tiempo.year ORDER BY f.estudiantes_por_docente DESC) AS rank_efficiency
FROM gold.fact_relacion_estudiante_docente f
JOIN gold.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN gold.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.is_active = TRUE
    AND f.estudiantes_por_docente IS NOT NULL
    AND f.total_estudiantes > 0
ORDER BY d_tiempo.year DESC, rank_efficiency ASC
LIMIT 20;

-- =============================================================================
-- 9. REPORTE EJECUTIVO: RESUMEN POR CLASIFICACIÓN SUE
-- =============================================================================

SELECT 
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_tiempo.year,
    
    -- Conteos
    COUNT(DISTINCT d_ies.dim_ies_id) AS num_instituciones,
    
    -- Estudiantes
    SUM(f.total_estudiantes) AS total_estudiantes,
    ROUND(AVG(f.total_estudiantes)::NUMERIC, 0) AS promedio_estudiantes,
    
    -- Docentes
    SUM(f.total_docentes) AS total_docentes,
    ROUND(AVG(f.total_docentes)::NUMERIC, 0) AS promedio_docentes,
    
    -- Ratios
    ROUND((SUM(f.total_estudiantes)::DECIMAL / NULLIF(SUM(f.total_docentes), 0)), 2) 
        AS ratio_global,
    ROUND(AVG(f.estudiantes_por_docente)::NUMERIC, 2) AS promedio_ratio
FROM gold.fact_relacion_estudiante_docente f
JOIN gold.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN gold.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.is_active = TRUE
GROUP BY d_ies.es_sue, d_tiempo.year
ORDER BY d_tiempo.year DESC, d_ies.es_sue;

-- =============================================================================
-- 10. EXPORTACIÓN: FORMATO PARA EXCEL/CSV
-- =============================================================================

-- Vista completa para exportación
SELECT 
    d_ies.ies_name AS "Institución",
    d_ies.sector_ies AS "Sector",
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS "Clasificación",
    d_tiempo.year AS "Año",
    f.total_estudiantes AS "Total Estudiantes",
    f.total_docentes AS "Total Docentes",
    f.estudiantes_por_docente AS "Estudiantes por Docente"
FROM gold.fact_relacion_estudiante_docente f
JOIN gold.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN gold.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.is_active = TRUE
ORDER BY d_tiempo.year DESC, d_ies.ies_name ASC;

-- =============================================================================
-- AUDITORÍA: VER LOGS DEL PIPELINE
-- =============================================================================

SELECT * FROM audit.pipeline_log
ORDER BY created_at DESC
LIMIT 20;
