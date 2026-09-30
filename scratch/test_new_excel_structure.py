import pandas as pd
from processing import process_excel

temp_excel_path = "scratch/temp_new_structure_test.xlsx"

data = {
    'Ciclo': ['BASE / CHASIS'],
    'Día': ['lunes, 20 de julio de 2026'],
    'Entrenamiento principal': ['Carrera 10 km Z2 con 6 rectas de 100m. Natación 1.800m de alineación.'],
    'Explicación': ['Abre el bloque con economía: el rodaje queda gobernado por pulso y RPE 3-4.'],
    'Deporte 1': ['Carrera'],
    'Nombre del Entreno 1': ['Rodaje base + rectas'],
    'Entrenamiento Intervals 1': [
        'Main Set\n- 8.4km Z2 Pace\n6x\n- 0.1km Z4 Pace\n- 0.1km Z1 Pace'
    ],
    'Deporte 2': ['Natación'],
    'Nombre del Entreno 2': ['Alineación y rotación 1.800m'],
    'Entrenamiento Intervals 2': [
        'Natación Técnica — alineación y rotación. Volumen total: 1.800m.\n\nCalentamiento:\n300m crol suave.\n\nTécnica:\n8x50m.\n\nBloque principal:\n5x100m crol aeróbico.'
    ],
    'Categoría': ['WORKOUT']
}

df_orig = pd.DataFrame(data)
df_orig.to_excel(temp_excel_path, index=False)

mapping = {
    'Día': 'Día',
    'IntervalsText': 'Entrenamiento Intervals 1',
    'SportType': 'Deporte 1',
    'Name': 'Nombre del Entreno 1',
    'IntervalsText2': 'Entrenamiento Intervals 2',
    'SportType2': 'Deporte 2',
    'Name2': 'Nombre del Entreno 2',
    'Category': 'Categoría',
    'ExplicacionSemana': 'Explicación'
}

print("Procesando Excel simulado con la NUEVA estructura...")
df_res = process_excel(temp_excel_path, column_mapping=mapping)

print(f"\nTotal filas resultantes: {len(df_res)}")
for idx, row in df_res.iterrows():
    print(f"\n====================== FILA {idx} ======================")
    print(f"Día: {row['Día']}")
    print(f"Deporte (SportType): {row['SportType']}")
    print(f"Nombre (Name): {row['Name']}")
    print(f"Categoría: {row['Category']}")
    print(f"Contenido IntervalsText:\n{row['IntervalsText']}")
