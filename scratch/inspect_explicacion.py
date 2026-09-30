import pandas as pd
excel_path = "Planificación temporada 25-26.xlsx"
df = pd.read_excel(excel_path, sheet_name="Entrenos")
print("Total rows:", len(df))
# Filter rows where 'Explicación semana' is not null
df_exp = df[df['Explicación semana'].notna() & (df['Explicación semana'].astype(str).str.strip() != "")]
print("\nRows with 'Explicación semana' filled:")
for idx, row in df_exp.head(10).iterrows():
    print(f"\nRow {idx} | Date: {row['Día']}")
    content = str(row['Explicación semana'])
    content_ascii = content.encode('ascii', errors='replace').decode('ascii')
    print(f"Content: {repr(content_ascii)}")
