import pandas as pd
from processing import process_excel

excel_path = r"d:\Users\juan_\Documents\Juanan\Programación\Carga de temporada intervals.uci\Temporada 26-27.xlsx"

# Definir el mapeo
mapping = {
    'Día': 'Día',
    'IntervalsText': 'Entrenamiento principal',
    'SportType': 'Deporte',
    'Name': 'Nombre del Entreno',
    'Category': 'Categoría',
    'ExplicacionSemana': 'Explicación'
}

df = process_excel(excel_path, sheet_name='Entrenamientos', column_mapping=mapping)

print("\nVerificando si hay filas que contienen la palabra 'semana' en la columna Día:")
semana_dias = df[df['Día'].astype(str).str.contains('semana', case=False, na=False)]
print(f"Filas con 'semana' en Día: {len(semana_dias)}")
if len(semana_dias) > 0:
    print(semana_dias[['Día', 'SportType', 'Name']])

print("\nBuscando entrenamientos del tipo 'Test' o '5K' o 'Fuego':")
test_rows = df[df['IntervalsText'].astype(str).str.contains('test|5k|fuego', case=False, na=False)]
print(f"Filas encontradas: {len(test_rows)}")
for idx, row in test_rows.head(10).iterrows():
    print(f"--- Día: {row['Día']} | Deporte: {row['SportType']} | Categoría: {row['Category']} ---")
    print("Original / Mapped Name:", row['Name'])
    print(row['IntervalsText'])
    print("-" * 50)
