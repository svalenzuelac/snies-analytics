# 🔧 Troubleshooting - Solución de Problemas

Guía para resolver problemas comunes durante la instalación, configuración y ejecución de SNIES Analytics.

---

## 📋 Tabla de Problemas

1. [Docker no inicia](#1-docker-no-inicia)
2. [Puerto 5432 en uso](#2-puerto-5432-en-uso)
3. [ETL falla con "Connection refused"](#3-etl-falla-con-connection-refused)
4. [Metabase muestra "base de datos vacía"](#4-metabase-muestra-base-de-datos-vacía)
5. ["Too many connections" error](#5-too-many-connections-error)
6. [PostgreSQL no persiste datos](#6-postgresql-no-persiste-datos)
7. [Metabase no conecta a PostgreSQL](#7-metabase-no-conecta-a-postgresql)
8. [Error de permisos en directorios](#8-error-de-permisos-en-directorios)
9. [CPU/Memoria al 100%](#9-cpumemoria-al-100)

---

## 1. Docker no inicia

### Síntoma
```
docker-compose up
# Error: Docker daemon is not running
```

### Soluciones

#### Windows
```bash
# Opción 1: Reiniciar Docker Desktop
# - Click en ícono Docker en system tray
# - Seleccionar "Restart Docker"

# Opción 2: Desde PowerShell (como Admin)
Restart-Service docker

# Opción 3: Verificar que está instalado
docker --version
```

#### macOS
```bash
# Opción 1: Reiniciar Docker Desktop
# - Menú Apple > System Settings > General
# - O presionar Cmd+Espacio y buscar "Docker"

# Opción 2: Desde terminal
brew services restart docker
```

#### Linux
```bash
# Opción 1: Iniciar daemon
sudo systemctl start docker

# Opción 2: Habilitar en boot
sudo systemctl enable docker

# Opción 3: Verificar estado
sudo systemctl status docker
```

### Verificación
```bash
docker ps
# Debería mostrar contenedores en ejecución
```

---

## 2. Puerto 5432 en uso

### Síntoma
```
docker-compose up
# Error: bind: address already in use :::5432
```

### Causa
PostgreSQL ya está corriendo en tu máquina (versión local) o Docker tiene un contenedor antiguo.

### Soluciones

#### Opción 1: Cambiar puerto en docker-compose.yaml

```yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Cambiar aquí (primero es externo)
```

Luego conectar con:
```bash
psql -h localhost -p 5433 -U postgres
```

#### Opción 2: Detener PostgreSQL local

```bash
# Windows
Get-Process postgres | Stop-Process -Force

# macOS
brew services stop postgresql@15

# Linux
sudo systemctl stop postgresql
```

#### Opción 3: Remover contenedor antiguo

```bash
# Listar contenedores
docker ps -a

# Remover contenedor específico
docker rm -f snies-analytics-postgres

# Remover todos los contenedores
docker system prune -a
```

### Verificación
```bash
# Verificar que puerto está libre
netstat -an | grep 5432  # Linux/macOS
netstat -an | findstr 5432  # Windows
```

---

## 3. ETL falla con "Connection refused"

### Síntoma
```
docker-compose logs -f etl
# Error: could not connect to server: Connection refused
```

### Causa
PostgreSQL no está listo cuando ETL intenta conectar.

### Soluciones

#### Opción 1: Esperar más tiempo (recomendado)

```bash
# Ver logs de PostgreSQL
docker-compose logs -f postgres

# Esperar a ver esto:
# "database system is ready to accept connections"

# Luego iniciar ETL
docker-compose up etl
```

#### Opción 2: Aumentar timeout en docker-compose.yaml

```yaml
services:
  etl:
    depends_on:
      postgres:
        condition: service_healthy  # Esperar health check
    environment:
      - DB_CONNECT_TIMEOUT=30  # Aumentar a 30 segundos
```

#### Opción 3: Reiniciar solo ETL

```bash
# Si PostgreSQL está listo
docker-compose restart etl

# O ejecutar manualmente
docker-compose run etl python scripts/cargador_etl.py
```

### Verificación
```bash
# Probar conexión directamente
docker-compose exec postgres \
  psql -U postgres -d snies_analytics -c "SELECT 1;"

# Debería retornar: 1
```

---

## 4. Metabase muestra "base de datos vacía"

### Síntoma
```
Abrir http://localhost:3000
# Metabase conecta pero no ve tablas
```

### Causa
Schema.sql no se ejecutó o ETL no completó.

### Soluciones

#### Opción 1: Ejecutar schema manualmente

```bash
# Copiar schema a contenedor
docker cp sql/schema.sql snies-analytics-postgres:/tmp/

# Ejecutar
docker exec snies-analytics-postgres \
  psql -U postgres -d snies_analytics -f /tmp/schema.sql
```

#### Opción 2: Verificar que ETL completó

```bash
# Ver logs
docker-compose logs etl | grep -i "completed\|error"

# Si hay errores, ver completos
docker-compose logs etl
```

#### Opción 3: Recargar BD en Metabase

```
1. Abrir http://localhost:3000
2. Gear icon (⚙️) > Admin Settings
3. Databases > snies_analytics
4. Sync database schema
5. Esperar 30 segundos
```

#### Opción 4: Reiniciar todo

```bash
# Parar todo
docker-compose down -v

# Limpiar volúmenes (⚠️ borra datos!)
docker volume prune

# Reiniciar
docker-compose up --build

# Esperar 3-5 minutos
```

### Verificación
```bash
# Conectar y verificar tablas
docker exec snies-analytics-postgres \
  psql -U postgres -d snies_analytics -c "\dt oro.*"

# Debería mostrar:
# fact_relacion_estudiante_docente
# dim_ies, dim_tiempo, dim_sector
```

---

## 5. "Too many connections" error

### Síntoma
```
Error: FATAL: too many connections for role "postgres"
```

### Causa
Múltiples aplicaciones conectadas y se alcanzó el límite.

### Soluciones

#### Opción 1: Aumentar límite en docker-compose.yaml

```yaml
services:
  postgres:
    command:
      - "postgres"
      - "-c"
      - "max_connections=200"  # Aumentar de 100 a 200
```

Luego:
```bash
docker-compose down
docker-compose up --build
```

#### Opción 2: Cerrar conexiones inactivas

```bash
# Conectar a PostgreSQL
docker exec -it snies-analytics-postgres psql -U postgres

# Dentro de psql:
SELECT pid, usename, application_name, state 
FROM pg_stat_activity 
WHERE state = 'idle';

-- Matar conexiones
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';
```

#### Opción 3: Verificar conexiones activas

```bash
# Ver cuántas conexiones hay
docker exec snies-analytics-postgres \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## 6. PostgreSQL no persiste datos

### Síntoma
```
docker-compose down
docker-compose up
# Los datos desaparecieron
```

### Causa
Volúmenes de Docker no están configurados correctamente.

### Soluciones

#### Opción 1: Verificar volúmenes en docker-compose.yaml

```yaml
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data  # ✅ REQUERIDO

volumes:
  postgres_data:
    driver: local
```

#### Opción 2: Crear volumen manualmente

```bash
docker volume create postgres_data

# Verificar
docker volume ls | grep postgres
```

#### Opción 3: Usar path absoluto (alternativa)

```yaml
services:
  postgres:
    volumes:
      - /var/lib/postgresql/data:/var/lib/postgresql/data
```

### Verificación
```bash
# Listar volúmenes
docker volume ls

# Inspeccionar volumen
docker volume inspect snies-analytics_postgres_data
```

---

## 7. Metabase no conecta a PostgreSQL

### Síntoma
```
Metabase: "Connection failed"
```

### Causa
Credenciales incorrectas o Network aislada.

### Soluciones

#### Opción 1: Verificar credenciales

En Metabase:
```
Admin Settings > Databases > Add database
Database type: PostgreSQL
Host: postgres  (nombre del servicio, NOT localhost)
Port: 5432
Username: postgres
Password: postgres
Database: snies_analytics
```

#### Opción 2: Verificar Network

```yaml
services:
  postgres:
    networks:
      - snies_network
  metabase:
    networks:
      - snies_network

networks:
  snies_network:
    driver: bridge
```

#### Opción 3: Test de conectividad

```bash
# Desde contenedor Metabase
docker exec snies-analytics-metabase \
  curl -v postgres:5432

# Debería conectar (no error de timeout)
```

### Verificación
```bash
# Conectar desde Metabase
docker-compose exec postgres \
  psql -U postgres -d snies_analytics -c "SELECT 1;"
```

---

## 8. Error de permisos en directorios

### Síntoma
```
Error: Permission denied
  for '/var/lib/postgresql/data'
```

### Causa
Permisos de directorios incorrectos (Linux/macOS).

### Soluciones

#### Linux
```bash
# Dar permisos a carpeta local
sudo chown -R $(whoami):$(whoami) ./sql/

# O ejecutar Docker con usuario específico
docker-compose -f docker-compose.yml up
```

#### macOS
```bash
# Dar permisos
chmod -R 755 ./sql/

# Verificar propiedad
ls -la sql/
```

#### Windows (PowerShell como Admin)
```powershell
# Limpiar y reintentar
docker-compose down -v
docker system prune -a

# Reiniciar Docker
Restart-Service docker

# Intentar de nuevo
docker-compose up --build
```

---

## 9. CPU/Memoria al 100%

### Síntoma
```
Docker utiliza toda la CPU o RAM
Sistema lento o sin respuesta
```

### Causa
- Query sin optimizar corriendo en background
- PostgreSQL con caché insuficiente
- Metabase cargando mucho

### Soluciones

#### Opción 1: Limitar recursos en docker-compose.yaml

```yaml
services:
  postgres:
    mem_limit: 2gb  # Máximo 2GB RAM
    memswap_limit: 2gb
    cpus: 2.0  # Máximo 2 cores

  metabase:
    mem_limit: 1gb
    cpus: 1.0

  etl:
    mem_limit: 512mb
    cpus: 1.0
```

#### Opción 2: Matar query que consume recursos

```bash
# Identificar query larga
docker exec snies-analytics-postgres \
  psql -U postgres -c "SELECT pid, query, query_start FROM pg_stat_activity WHERE state = 'active';"

# Matar proceso
docker exec snies-analytics-postgres \
  psql -U postgres -c "SELECT pg_terminate_backend(PID);"
```

#### Opción 3: Limpiar datos temporales

```bash
# Vaciar caché de PostgreSQL
docker exec snies-analytics-postgres \
  psql -U postgres -c "VACUUM ANALYZE;"
```

#### Opción 4: Reiniciar servicios

```bash
# Parar todo
docker-compose stop

# Esperar 30 segundos
sleep 30

# Reiniciar
docker-compose up
```

---

## 🆘 Problemas Avanzados

### Query muy lenta
```bash
# Ejecutar EXPLAIN ANALYZE
docker exec snies-analytics-postgres psql -U postgres -d snies_analytics << EOF
EXPLAIN ANALYZE
SELECT * FROM oro.v_relacion_estudiante_docente WHERE año = 2024;
EOF
```

### Corromper índices
```bash
# Reindexar
docker exec snies-analytics-postgres psql -U postgres -d snies_analytics << EOF
REINDEX DATABASE snies_analytics;
EOF
```

### Recuperar backup
```bash
# Crear backup
docker exec snies-analytics-postgres \
  pg_dump -U postgres snies_analytics > backup.sql

# Restaurar
docker exec -i snies-analytics-postgres \
  psql -U postgres < backup.sql
```

---

## 📞 Si nada funciona

### Reset completo (última opción)

```bash
# 1. Parar todo
docker-compose down -v

# 2. Limpiar Docker
docker system prune -a --volumes

# 3. Eliminar volúmenes persistentes
docker volume rm snies-analytics_postgres_data

# 4. Reiniciar Docker Desktop
# Windows: Restart Docker
# macOS: Quit y reabrir Docker
# Linux: sudo systemctl restart docker

# 5. Clonar de nuevo
rm -rf snies-analytics
git clone https://github.com/TU_USUARIO/snies-analytics.git
cd snies-analytics

# 6. Reintentar
docker-compose up --build
```

### Reporte de Bug
Si el problema persiste, crea un issue en GitHub con:
1. SO (Windows/Mac/Linux) + versión
2. Docker version: `docker --version`
3. Logs completos: `docker-compose logs > logs.txt`
4. Pasos para reproducir
5. Error exacto (screenshot)

---

## ✅ Checklist de Diagnóstico

```bash
# 1. Verificar Docker
docker ps
docker --version

# 2. Verificar servicios
docker-compose ps

# 3. Ver logs
docker-compose logs --tail=50

# 4. Conectar a BD
docker-compose exec postgres psql -U postgres

# 5. Acceder a Metabase
curl http://localhost:3000

# 6. Verificar volúmenes
docker volume ls

# 7. Ping entre contenedores
docker-compose exec etl ping postgres
```

---

## 📚 Enlaces Útiles

- [Docker Issues](https://docs.docker.com/config/containers/resource_constraints/)
- [PostgreSQL Troubleshooting](https://www.postgresql.org/docs/current/runtime-config.html)
- [Metabase Help](https://www.metabase.com/learn)
- [Stack Overflow Tag postgresql](https://stackoverflow.com/questions/tagged/postgresql)

---

**Última actualización**: Abril 2026  
**Versión**: 2.0
