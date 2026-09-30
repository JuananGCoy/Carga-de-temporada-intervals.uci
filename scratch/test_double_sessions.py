import pandas as pd
from processing import process_excel

# Vamos a simular la importación de un archivo Excel creando un DataFrame similar
# y guardándolo en un archivo Excel temporal para que process_excel lo lea.
temp_excel_path = "scratch/temp_test_double.xlsx"

data = {
    'Día': ['lunes, 13 de julio de 2026', 'martes, 14 de julio de 2026'],
    'Entrenamiento principal': [
        'Carrera: 10 km rodaje en Z2 + Natación: 1500m aeróbico medio',
        'Ciclismo: 60 min en Z1 a cadencia alta.'
    ],
    'Entrenamiento Intervals 1': [
        'Warmup\n- 3km Z1 Pace\nMain Set\n- 7km Z2 Pace',
        'Warmup\n- 10m Z1\nMain Set\n- 40m Z2\nCooldown\n- 10m Z1'
    ],
    'Entrenamiento Intervals 2': [
        'Natación: 1500m aeróbico medio',
        '' # Vacío, solo una sesión
    ]
}

df_orig = pd.DataFrame(data)
df_orig.to_excel(temp_excel_path, index=False)

# Mapeo
mapping = {
    'Día': 'Día',
    'IntervalsText': 'Entrenamiento Intervals 1',
    'IntervalsText2': 'Entrenamiento Intervals 2',
    'SportType': None,
    'Name': None,
    'Category': None,
    'ExplicacionSemana': None
}

print("Procesando Excel simulado...")
df_processed = process_excel(temp_excel_path, column_mapping=mapping)

print(f"\nTotal filas resultantes: {len(df_processed)}")
for idx, row in df_processed.iterrows():
    print(f"\n--- Fila {idx} | Fecha: {row['Día']} | Deporte: {row['SportType']} | Categoría: {row['Category']} ---")
    print("Contenido IntervalsText:")
    print(row['IntervalsText'])
    print("-" * 40)
