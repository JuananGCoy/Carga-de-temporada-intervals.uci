import pandas as pd
excel_path = "Planificación temporada 25-26.xlsx"
try:
    xl = pd.ExcelFile(excel_path)
    print("Sheets in Excel:", xl.sheet_names)
    for sheet in xl.sheet_names[:3]:
        df = xl.parse(sheet)
        print(f"\nSheet: {sheet}")
        print("Columns:", list(df.columns))
        print("First 3 rows:\n", df.head(3))
except Exception as e:
    print("Error reading Excel:", e)
