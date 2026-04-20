"""
Script para arreglar columnas del CSV
Ejecutar: python fix_csv_columns.py
"""

import pandas as pd

print("=" * 70)
print("🔧 ARREGLADOR DE COLUMNAS CSV SNIES")
print("=" * 70)

try:
    # Leer el CSV
    df = pd.read_csv('data/raw/snies_with_docentes.csv', encoding='utf-8')
    
    print(f"\n✅ CSV leído: {len(df)} registros")
    print(f"\nColumnas actuales:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    # Normalizar columnas
    df.columns = df.columns.str.strip().str.lower()
    
    print(f"\nColumnas normalizadas:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    # Guardar
    df.to_csv('data/raw/snies_with_docentes.csv', index=False, encoding='utf-8')
    
    print("\n" + "=" * 70)
    print("✅ CSV ACTUALIZADO CORRECTAMENTE")
    print("=" * 70)
    print("\nSiguiente paso: docker-compose up")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nVerifica que estés en la carpeta C:\\snies")
