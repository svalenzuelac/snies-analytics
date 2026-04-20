# 🚀 Inicio Rápido - SNIES Analytics

**Solo 3 comandos para tener el sistema funcionando**

---

## 1️⃣ Clonar Repositorio

```bash
git clone https://github.com/TU_USUARIO/snies-analytics.git
cd snies-analytics
```

## 2️⃣ Iniciar Sistema

```bash
docker-compose up --build
```

Espera 2-3 minutos. Verás:
- ✅ PostgreSQL listo
- ✅ Descargador SNIES completado
- ✅ ETL completado
- ✅ Metabase iniciado

## 3️⃣ Acceder a Herramientas

| Herramienta | URL | Usuario | Contraseña |
|---|---|---|---|
| **Metabase** | http://localhost:3000 | admin@localhost | metabase123 |
| **PgAdmin** | http://localhost:5050 | admin@pgadmin.com | admin |
| **PostgreSQL** | localhost:5432 | postgres | postgres |

---

## 📊 Primeros Pasos en Metabase

1. Abre http://localhost:3000
2. Haz clic en **Dashboards** (izquierda)
3. Explora los 3 dashboards precargados:
   - 📈 **Relación Estudiante/Docente** - Todos los datos
   - 🏆 **Top 10 Universidades** - Rankings
   - 📊 **SUE vs No SUE** - Comparativa

---

## 🔍 Verificar Datos

```bash
# Conectar a PostgreSQL
docker-compose exec postgres psql -U postgres -d snies_analytics

# Dentro de psql, ejecuta:
SELECT COUNT(*) FROM oro.dim_ies;           -- Debería retornar: 117
SELECT COUNT(*) FROM oro.fact_relacion_estudiante_docente;  -- 351
SELECT * FROM oro.v_top_ies_by_ratio LIMIT 10;  -- Ver top 10
```

---

## ❌ Si algo falla

Ver **TROUBLESHOOTING.md** en `/docs/TROUBLESHOOTING.md`

Problemas más comunes:
- Puerto 5432 en uso → cambiar en docker-compose.yaml
- CSV no encontrado → revisar logs: `docker-compose logs -f etl`
- Metabase sin tablas → esperar y recargar en navegador

---

## 📚 Documentación Completa

- **README.md** - Guía completa (instalación, arquitectura, queries)
- **ENTREGA_FINAL.md** - Checklist de requisitos del reto
- **docs/ARQUITECTURA.md** - Detalles técnicos
- **docs/TROUBLESHOOTING.md** - Solución de problemas
- **docs/ESCALABILIDAD.md** - Plan de crecimiento
- **VALIDACION_RUTAS.md** - Verificación de compatibilidad

---

## 🎯 Siguientes Pasos

1. Subir a GitHub
2. Compartir enlace
3. Demo en vivo

**¡Listo para presentación!** ✨
