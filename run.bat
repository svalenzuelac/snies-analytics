@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo SNIES ANALYTICS - EJECUCION COMPLETA
echo ================================================================
echo.

echo Creando estructura de directorios...
if not exist "datos\crudos" mkdir datos\crudos
if not exist "sql" mkdir sql
copy schema.sql sql\schema.sql >nul 2>&1
echo OK

echo.
echo Limpiando ejecuciones anteriores...
docker-compose down >nul 2>&1

echo.
echo ================================================================
echo INICIANDO PIPELINE COMPLETO (Postgres + ETL + PgAdmin)
echo ================================================================
echo.
echo Esto puede tardar 3-5 minutos la primera vez.
echo Por favor espera...
echo.

docker-compose up

echo.
echo ================================================================
echo COMPLETADO
echo ================================================================
echo.
echo PostgreSQL:
echo   Host: localhost:5432
echo   Base de datos: snies_analytics
echo   Usuario: postgres
echo   Contrasena: postgres
echo.
echo PgAdmin:
echo   URL: http://localhost:5050
echo   Usuario: admin@pgadmin.com
echo   Contrasena: admin
echo.
echo Para conectar a PostgreSQL desde PgAdmin:
echo   Host: postgres
echo   Puerto: 5432
echo   Usuario: postgres
echo   Contrasena: postgres
echo.

pause
