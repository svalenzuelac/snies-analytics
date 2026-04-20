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

# Copiar scripts
COPY descargador_snies_production_final.py .
COPY etl_loader.py .

# Crear directorios
RUN mkdir -p /app/data/raw /app/sql

# Default: mostrar help
CMD ["python", "--version"]
