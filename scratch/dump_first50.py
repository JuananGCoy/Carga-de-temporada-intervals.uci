import pandas as pd

file_path = "Temporada 26-27.xlsx"
df = pd.read_excel(file_path, sheet_name="Entrenamientos")

# Show first 50 rows
for idx, row in df.head(50).iterrows():
    dia = str(row.get('Día', '')).encode('ascii', errors='replace').decode('ascii')
    ep = str(row.get('Entrenamiento principal', '')).encode('ascii', errors='replace').decode('ascii')
    cat = str(row.get('Categoría', ''))
    comp = str(row.get('Competiciones', ''))
    if ep and ep != 'nan':
        print(f"ROW {idx} | {dia}")
        print(f"  TEXT: {ep}")
        if cat and cat != 'nan':
            print(f"  CAT: {cat}")
        if comp and comp != 'nan':
            print(f"  COMP: {comp}")
        print()
