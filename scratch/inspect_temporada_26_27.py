import pandas as pd
import json

file_path = "Temporada 26-27.xlsx"
try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheets: {xl.sheet_names}")
    for sheet in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet)
        print(f"\n--- Sheet: {sheet} ---")
        print(f"Columns: {list(df.columns)}")
        print(f"Head:\n{df.head(3)}")
except Exception as e:
    print(f"Error reading excel: {e}")
