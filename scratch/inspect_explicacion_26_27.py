import pandas as pd

file_path = "Temporada 26-27.xlsx"
df = pd.read_excel(file_path, sheet_name="Entrenamientos")
print(df[['Día', 'Explicación']].dropna().head(10))
