# 🤝 Guía de Contribución

Gracias por tu interés en contribuir a **SNIES Analytics**. Este documento proporciona directrices para mantener la calidad y consistencia del proyecto.

---

## 📋 Tabla de Contenidos

1. [Código de Conducta](#código-de-conducta)
2. [Reportar Bugs](#reportar-bugs)
3. [Sugerir Mejoras](#sugerir-mejoras)
4. [Estándares de Código](#estándares-de-código)
5. [Proceso de Pull Request](#proceso-de-pull-request)
6. [Configuración de Desarrollo](#configuración-de-desarrollo)

---

## 💻 Código de Conducta

Esperamos que todos los contribuyentes mantengan un ambiente respetuoso y profesional.

- Sé considerado con otros desarrolladores
- Proporciona feedback constructivo
- Acepta crítica constructiva
- Enfócate en lo que es mejor para la comunidad

---

## 🐛 Reportar Bugs

### Antes de reportar
- Verifica que el bug no esté ya reportado
- Revisa la sección [Troubleshooting](TROUBLESHOOTING.md)
- Intenta reproducir el bug con la última versión

### Cómo reportar

Abre un **GitHub Issue** con el siguiente formato:

```markdown
## Descripción del Bug
[Descripción clara y concisa del problema]

## Pasos para Reproducir
1. [Primer paso]
2. [Segundo paso]
3. ...

## Comportamiento Esperado
[Qué debería suceder]

## Comportamiento Actual
[Qué está sucediendo realmente]

## Environment
- SO: [Windows/Mac/Linux]
- Docker Version: [versión]
- Python Version: [3.11]

## Logs Relevantes
[Pega aquí los logs del error]
```

---

## 💡 Sugerir Mejoras

### Antes de sugerir
- Verifica que la mejora no esté ya documentada
- Considera el impacto en la arquitectura existente
- Piensa en casos de uso reales

### Cómo sugerir

Abre un **GitHub Discussion** o **Issue** con:

```markdown
## Descripción de la Mejora
[Explicación clara de la mejora propuesta]

## Justificación
[Por qué esta mejora es valiosa para el proyecto]

## Ejemplo de Uso
[Cómo se vería la mejora en acción]

## Alternativas Consideradas
[Otras soluciones que no fueron seleccionadas]

## Impacto
[Impacto en performance, compatibilidad, mantenimiento, etc.]
```

---

## 💎 Estándares de Código

### Python

```python
# ✅ BUENO
def cargar_datos_desde_snies(año: int) -> pd.DataFrame:
    """
    Carga datos SNIES para el año especificado.
    
    Args:
        año: Año a procesar (2022-2024)
    
    Returns:
        DataFrame con datos cargados
    """
    if año not in [2022, 2023, 2024]:
        raise ValueError(f"Año {año} no soportado")
    
    # Lógica aquí
    return df


# ❌ MALO
def load_data(y):
    # This loads snies data
    if y < 2022 or y > 2024:
        print("Invalid year")
        return None
    # Lógica
    return df
```

**Guías**:
- Usa **type hints** en todas las funciones
- Docstrings en formato **Google** o **NumPy**
- Nombres descriptivos: `snies_data` no `d` o `data123`
- Máximo 88 caracteres por línea
- Usa **black** para formateo

```bash
pip install black
black scripts/
```

### SQL

```sql
-- ✅ BUENO
SELECT 
    dim_ies.nombre_ies,
    dim_sector.nombre_sector,
    fact_relacion.ratio_estudiante_docente
FROM oro.fact_relacion_estudiante_docente fact_relacion
INNER JOIN oro.dim_ies ON fact_relacion.dim_ies_id = dim_ies.id
INNER JOIN oro.dim_sector ON fact_relacion.dim_sector_id = dim_sector.id
WHERE dim_tiempo.año = 2024
ORDER BY fact_relacion.ratio_estudiante_docente DESC;

-- ❌ MALO
select a.nombre_ies, b.nombre_sector, c.ratio
from oro.fact_relacion_estudiante_docente c
inner join oro.dim_ies a on c.dim_ies_id = a.id
inner join oro.dim_sector b on c.dim_sector_id = b.id
where c.año = 2024;
```

**Guías**:
- UPPERCASE para keywords (SELECT, WHERE, FROM)
- Indentación de 4 espacios
- Un elemento por línea en SELECT
- Aliasas descriptivos
- Comments para lógica compleja

### Documentación Markdown

```markdown
# ✅ BUENO
## Instalación

Para instalar la solución:

1. Clonar el repositorio
2. Ejecutar docker-compose up

### Requisitos Previos
- Docker Desktop
- 2GB RAM

# ❌ MALO
## install
just run docker-compose up and it will work
```

**Guías**:
- Títulos jerárquicos (H2, H3, no H1)
- Listas numeradas para pasos secuenciales
- Bloques de código con lenguaje especificado
- Enlaces internos a otras secciones

---

## 🔀 Proceso de Pull Request

### 1. Preparar tu rama

```bash
# Partir de main actualizada
git checkout main
git pull origin main

# Crear rama descriptiva
git checkout -b feature/agregar-dashboard-sue
# o
git checkout -b fix/corregir-nulos-en-carga
```

**Nombres de rama**:
- `feature/descripcion` - Nueva funcionalidad
- `fix/descripcion` - Corrección de bug
- `docs/descripcion` - Solo documentación
- `refactor/descripcion` - Refactorización

### 2. Hacer cambios

```bash
# Hacer cambios, testear localmente
python scripts/cargador_etl.py
docker-compose up --build

# Commit con mensaje descriptivo
git add .
git commit -m "feat: Agregar validación de datos nulos en capa Plata"
```

**Formato de commits** (Conventional Commits):
- `feat:` Nueva funcionalidad
- `fix:` Corrección de bug
- `docs:` Cambios en documentación
- `refactor:` Cambios sin funcionalidad nueva
- `test:` Agregar/modificar tests
- `perf:` Mejoras de performance

### 3. Push y Pull Request

```bash
git push origin feature/descripcion
```

**Template de PR**:

```markdown
## Descripción
[Breve descripción de qué cambia]

## Tipo de Cambio
- [ ] Bug fix
- [ ] Nueva funcionalidad
- [ ] Cambio en documentación
- [ ] Refactorización

## Cambios Realizados
- [x] Cambio 1
- [x] Cambio 2

## Pruebas Realizadas
- [x] Ejecución local: docker-compose up
- [x] Queries de validación ejecutadas
- [x] Metabase actualizado

## Checklist
- [x] Mi código sigue los estándares del proyecto
- [x] He actualizado la documentación
- [x] No hay errores en los logs
- [x] He probado en ambiente local

## Screenshots (si aplica)
[Incluir screenshots de dashboards, etc.]
```

### 4. Revisión y Merge

- Mínimo 1 approval requerido
- Feedback será constructivo y respetuoso
- Después de approval, mergear a `main`

---

## 🛠️ Configuración de Desarrollo

### Entorno Local

```bash
# 1. Clonar repositorio
git clone https://github.com/TU_USUARIO/snies-analytics.git
cd snies-analytics

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
pip install black flake8  # Tools de desarrollo

# 4. Pre-commit hooks (opcional)
pip install pre-commit
pre-commit install
```

### Ejecutar tests locales

```bash
# Docker compose
docker-compose up --build

# Verificar logs
docker-compose logs -f etl

# Conectar a DB
docker exec snies-analytics-postgres \
  psql -U postgres -d snies_analytics -c "SELECT COUNT(*) FROM oro.dim_ies;"
```

### Linting y Formatting

```bash
# Formatear código
black scripts/

# Verificar estilo
flake8 scripts/ --max-line-length=88

# SQL formatting (manual review)
# Usar IDE con SQL formatter o pgFormat
```

---

## 📚 Recursos Útiles

- [README.md](../README.md) - Documentación principal
- [ENTREGA_FINAL.md](../ENTREGA_FINAL.md) - Checklist de entrega
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Solución de problemas
- [ARQUITECTURA.md](ARQUITECTURA.md) - Detalles técnicos
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Pandas Docs](https://pandas.pydata.org/docs/)

---

## ❓ Preguntas?

- Abre una **GitHub Discussion**
- Revisa issues cerrados para contexto
- Consulta los docs antes de preguntar

---

## ✅ Gracias por Contribuir!

Tu contribución ayuda a mejorar SNIES Analytics para la comunidad de datos en Colombia.

**Happy coding! 🚀**
