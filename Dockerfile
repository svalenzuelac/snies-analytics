FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar scripts desde carpeta scripts/
COPY scripts/ /app/scripts/

# Copiar SQL
COPY sql/ /app/sql/

# Crear directorios de datos
RUN mkdir -p /app/data

# Default: mostrar help
CMD ["python", "--version"]
