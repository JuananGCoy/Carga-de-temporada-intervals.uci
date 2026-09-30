import pandas as pd
from processing import process_excel

temp_excel_path = "scratch/temp_four_sessions_test.xlsx"

data = {
    'Día': ['martes, 21 de julio de 2026'],
    'Explicación': ['Día con cuádruple sesión de volumen y movilidad.'],
    'Deporte 1': ['Carrera'],
    'Nombre 1': ['Rodaje mañanero'],
    'Intervals 1': ['Warmup\n- 10m Z1\nMain Set\n- 40m Z2'],
    
    'Deporte 2': ['Ciclismo'],
    'Nombre 2': ['Rodillo suave'],
    'Intervals 2': ['Main Set\n- 45m Z1'],
    
    'Deporte 3': ['Natación'],
    'Nombre 3': ['Trabajo de técnica'],
    'Intervals 3': ['Natación suave 1500m crol y estilos.'],

    'Deporte 4': ['Gimnasio'],
    'Nombre 4': ['Rutina de movilidad y core'],
    'Intervals 4': ['40 min de trabajo de fuerza y movilidad articular.']
}

df_orig = pd.DataFrame(data)
df_orig.to_excel(temp_excel_path, index=False)

mapping = {
    'Día': 'Día',
    'ExplicacionSemana': 'Explicación',
    'IntervalsText': 'Intervals 1',
    'SportType': 'Deporte 1',
    'Name': 'Nombre 1',
    'IntervalsText2': 'Intervals 2',
    'SportType2': 'Deporte 2',
    'Name2': 'Nombre 2',
    'IntervalsText3': 'Intervals 3',
    'SportType3': 'Deporte 3',
    'Name3': 'Nombre 3',
    'IntervalsText4': 'Intervals 4',
    'SportType4': 'Deporte 4',
    'Name4': 'Nombre 4',
}

print("Procesando Excel simulado con 4 SESIONES el mismo día...")
df_res = process_excel(temp_excel_path, column_mapping=mapping)

print(f"\nTotal filas resultantes: {len(df_res)}")
for idx, row in df_res.iterrows():
    print(f"\n----------------- SESIÓN / FILA {idx} -----------------")
    print(f"Día: {row['Día']}")
    print(f"Deporte: {row['SportType']}")
    print(f"Nombre: {row['Name']}")
    print(f"Categoría: {row['Category']}")
    print(f"Texto Intervals:\n{row['IntervalsText']}")
