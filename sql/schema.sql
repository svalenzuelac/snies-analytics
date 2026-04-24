/*
SNIES ANALYTICS - SCHEMA POSTGRESQL
Medallion Architecture: Bronce -> Plata -> Oro
*/

CREATE SCHEMA IF NOT EXISTS bronce;
CREATE SCHEMA IF NOT EXISTS plata;
CREATE SCHEMA IF NOT EXISTS oro;
CREATE SCHEMA IF NOT EXISTS auditoria;

/* ============================================================================
BRONCE: DATOS RAW (SIN PROCESAR)
============================================================================ */

DROP TABLE IF EXISTS bronce.snies_crudo CASCADE;

CREATE TABLE bronce.snies_crudo (
    id SERIAL PRIMARY KEY,
    nombre_ies VARCHAR(500) NOT NULL,
    año INT NOT NULL,
    total_estudiantes INT,
    total_docentes INT,
    estudiantes_por_docente DECIMAL(5, 2),
    sector_ies VARCHAR(100),
    clasificacion_sue VARCHAR(20),
    cargado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archivo_fuente VARCHAR(255)
);

CREATE INDEX idx_bronce_snies_ies_año ON bronce.snies_crudo(nombre_ies, año);
CREATE INDEX idx_bronce_snies_año ON bronce.snies_crudo(año);

/* ============================================================================
PLATA: DATOS PROCESADOS Y LIMPIOS
============================================================================ */

DROP TABLE IF EXISTS plata.snies_ies CASCADE;

CREATE TABLE plata.snies_ies (
    ies_id SERIAL PRIMARY KEY,
    nombre_ies VARCHAR(500) NOT NULL UNIQUE,
    sector_ies VARCHAR(50),
    es_sue BOOLEAN DEFAULT FALSE,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_plata_ies_nombre ON plata.snies_ies(nombre_ies);
CREATE INDEX idx_plata_ies_sue ON plata.snies_ies(es_sue);

DROP TABLE IF EXISTS plata.snies_estudiantes CASCADE;

CREATE TABLE plata.snies_estudiantes (
    estudiantes_id SERIAL PRIMARY KEY,
    ies_id INT NOT NULL REFERENCES plata.snies_ies(ies_id) ON DELETE CASCADE,
    año INT NOT NULL,
    total_estudiantes INT NOT NULL,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ies_id, año)
);

CREATE INDEX idx_plata_est_ies_año ON plata.snies_estudiantes(ies_id, año);
CREATE INDEX idx_plata_est_año ON plata.snies_estudiantes(año);

DROP TABLE IF EXISTS plata.snies_docentes CASCADE;

CREATE TABLE plata.snies_docentes (
    docentes_id SERIAL PRIMARY KEY,
    ies_id INT NOT NULL REFERENCES plata.snies_ies(ies_id) ON DELETE CASCADE,
    año INT NOT NULL,
    total_docentes INT NOT NULL,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ies_id, año)
);

CREATE INDEX idx_plata_doc_ies_año ON plata.snies_docentes(ies_id, año);
CREATE INDEX idx_plata_doc_año ON plata.snies_docentes(año);

/* ============================================================================
ORO: ANALÍTICA (STAR SCHEMA)
============================================================================ */

DROP TABLE IF EXISTS oro.dim_ies CASCADE;

CREATE TABLE oro.dim_ies (
    dim_ies_id SERIAL PRIMARY KEY,
    ies_id INT NOT NULL UNIQUE REFERENCES plata.snies_ies(ies_id),
    nombre_ies VARCHAR(500) NOT NULL,
    sector_ies VARCHAR(50),
    es_sue BOOLEAN,
    valido_desde DATE DEFAULT CURRENT_DATE,
    valido_hasta DATE,
    esta_activo BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_oro_dim_ies_nombre ON oro.dim_ies(nombre_ies);
CREATE INDEX idx_oro_dim_ies_sue ON oro.dim_ies(es_sue);

DROP TABLE IF EXISTS oro.dim_tiempo CASCADE;

CREATE TABLE oro.dim_tiempo (
    dim_tiempo_id SERIAL PRIMARY KEY,
    año INT UNIQUE NOT NULL,
    etiqueta_año VARCHAR(4) NOT NULL
);

INSERT INTO oro.dim_tiempo (año, etiqueta_año) 
VALUES (2022, '2022'), (2023, '2023'), (2024, '2024')
ON CONFLICT DO NOTHING;

DROP TABLE IF EXISTS oro.dim_sector CASCADE;

CREATE TABLE oro.dim_sector (
    dim_sector_id SERIAL PRIMARY KEY,
    codigo_sector VARCHAR(20) UNIQUE NOT NULL,
    nombre_sector VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255)
);

INSERT INTO oro.dim_sector (codigo_sector, nombre_sector, descripcion)
VALUES 
    ('oficial', 'Oficial', 'Institución pública/estatal'),
    ('privado', 'Privado', 'Institución privada'),
    ('desconocido', 'Desconocido', 'Sector sin clasificar')
ON CONFLICT DO NOTHING;

DROP TABLE IF EXISTS oro.hecho_relacion_estudiante_docente CASCADE;

CREATE TABLE oro.hecho_relacion_estudiante_docente (
    hecho_id SERIAL PRIMARY KEY,
    dim_ies_id INT NOT NULL REFERENCES oro.dim_ies(dim_ies_id),
    dim_tiempo_id INT NOT NULL REFERENCES oro.dim_tiempo(dim_tiempo_id),
    total_estudiantes INT NOT NULL,
    total_docentes INT NOT NULL,
    estudiantes_por_docente DECIMAL(5, 2),
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dim_ies_id, dim_tiempo_id)
);

CREATE INDEX idx_oro_hecho_ies ON oro.hecho_relacion_estudiante_docente(dim_ies_id);
CREATE INDEX idx_oro_hecho_tiempo ON oro.hecho_relacion_estudiante_docente(dim_tiempo_id);
CREATE INDEX idx_oro_hecho_ratio ON oro.hecho_relacion_estudiante_docente(estudiantes_por_docente);

/* ============================================================================
VISTAS ANALÍTICAS
============================================================================ */

DROP VIEW IF EXISTS oro.v_relacion_estudiante_docente CASCADE;

CREATE VIEW oro.v_relacion_estudiante_docente AS
SELECT
    d_ies.nombre_ies,
    d_ies.sector_ies,
    d_ies.es_sue,
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_tiempo.año,
    f.total_estudiantes,
    f.total_docentes,
    f.estudiantes_por_docente,
    RANK() OVER (PARTITION BY d_tiempo.año ORDER BY f.estudiantes_por_docente DESC) AS rank_ratio_desc,
    RANK() OVER (PARTITION BY d_tiempo.año ORDER BY f.estudiantes_por_docente ASC) AS rank_ratio_asc
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE
ORDER BY d_tiempo.año DESC, d_ies.nombre_ies ASC;

DROP VIEW IF EXISTS oro.v_promedio_por_sue CASCADE;

CREATE VIEW oro.v_promedio_por_sue AS
SELECT
    d_tiempo.año,
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS tipo,
    COUNT(DISTINCT d_ies.dim_ies_id) AS cantidad_ies,
    ROUND(AVG(f.total_estudiantes)::NUMERIC, 2) AS promedio_estudiantes,
    ROUND(AVG(f.total_docentes)::NUMERIC, 2) AS promedio_docentes,
    ROUND(AVG(f.estudiantes_por_docente)::NUMERIC, 2) AS promedio_ratio
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE
GROUP BY d_tiempo.año, d_ies.es_sue
ORDER BY d_tiempo.año DESC;

DROP VIEW IF EXISTS oro.v_top_ies_by_ratio CASCADE;

CREATE VIEW oro.v_top_ies_by_ratio AS
SELECT
    d_tiempo.año,
    RANK() OVER (PARTITION BY d_tiempo.año ORDER BY f.estudiantes_por_docente DESC) AS posicion,
    d_ies.nombre_ies,
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_ies.sector_ies,
    f.total_estudiantes,
    f.total_docentes,
    f.estudiantes_por_docente
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE;

DROP VIEW IF EXISTS oro.v_evolucion_ies CASCADE;

CREATE VIEW oro.v_evolucion_ies AS
SELECT
    d_ies.nombre_ies,
    d_ies.sector_ies,
    CASE WHEN d_ies.es_sue THEN 'SUE' ELSE 'No SUE' END AS clasificacion_sue,
    d_tiempo.año,
    f.total_estudiantes,
    f.total_docentes,
    f.estudiantes_por_docente,
    LAG(f.estudiantes_por_docente) OVER (
        PARTITION BY d_ies.dim_ies_id ORDER BY d_tiempo.año
    ) AS ratio_ano_anterior
FROM oro.hecho_relacion_estudiante_docente f
JOIN oro.dim_ies d_ies ON f.dim_ies_id = d_ies.dim_ies_id
JOIN oro.dim_tiempo d_tiempo ON f.dim_tiempo_id = d_tiempo.dim_tiempo_id
WHERE d_ies.esta_activo = TRUE;

/* ============================================================================
AUDITORÍA
============================================================================ */

DROP TABLE IF EXISTS auditoria.registro_pipeline CASCADE;

CREATE TABLE auditoria.registro_pipeline (
    log_id SERIAL PRIMARY KEY,
    etapa VARCHAR(50),
    estado VARCHAR(20),
    mensaje TEXT,
    registros_afectados INT,
    inicio_at TIMESTAMP,
    fin_at TIMESTAMP,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
