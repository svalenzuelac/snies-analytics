@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo SNIES ANALYTICS - SETUP EN WINDOWS
echo ================================================================
echo.

REM Crear estructura de carpetas
echo Creando estructura de directorios...
if not exist "datos\crudos" mkdir datos\crudos
if not exist "sql" mkdir sql
echo OK

REM Copiar schema a carpeta sql
echo.
echo Copiando schema.sql a carpeta sql...
copy schema.sql sql\schema.sql >nul 2>&1
echo OK

REM Crear la BD e importar schema
echo.
echo Inicializando PostgreSQL...
echo Espera a que PostgreSQL esté listo (10 segundos)...
timeout /t 10 /nobreak

REM Conectar a PostgreSQL e importar schema
echo.
echo Cargando schema en PostgreSQL...
psql -h localhost -U postgres -d snies_analytics -f schema.sql >nul 2>&1
if errorlevel 1 (
    echo ADVERTENCIA: No se pudo cargar schema automaticamente
    echo Por favor copia el contenido de schema.sql en PgAdmin manualmente
    echo URL: http://localhost:5050
    echo Usuario: admin@pgadmin.com / Contraseña: admin
)

echo.
echo OK

REM Ejecutar descargador
echo.
echo ================================================================
echo FASE 1: DESCARGANDO SNIES
echo ================================================================
python descargador_snies_produccion_final.py

if errorlevel 1 (
    echo ERROR en descargador
    pause
    exit /b 1
)

echo.
echo ================================================================
echo FASE 2: CARGANDO ETL
echo ================================================================
python cargador_etl.py

if errorlevel 1 (
    echo ERROR en cargador ETL
    pause
    exit /b 1
)

echo.
echo ================================================================
echo COMPLETADO EXITOSAMENTE
echo ================================================================
echo.
echo Base de datos: snies_analytics
echo Host: localhost:5432
echo Usuario: postgres / Contraseña: postgres
echo.
echo PgAdmin: http://localhost:5050
echo Usuario: admin@pgadmin.com / Contraseña: admin
echo.

pause
