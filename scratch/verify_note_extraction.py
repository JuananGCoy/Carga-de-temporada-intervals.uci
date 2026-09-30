import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from processing import process_excel

def test_notes():
    excel_path = "Planificación temporada 25-26.xlsx"
    sheet_name = "Entrenos"
    
    mapping = {
        'Día': 'Día',
        'IntervalsText': 'Entrenamiento principal',
        'SportType': None,
        'Name': None,
        'Category': None,
        'ExplicacionSemana': 'Explicación semana'
    }
    
    df = process_excel(excel_path, sheet_name=sheet_name, column_mapping=mapping)
    
    notes = df[df['Category'] == 'NOTE']
    print(f"Total NOTE rows found: {len(notes)}")
    
    weekly_explanations = df[df['Name'].fillna('').str.startswith('Objetivo:')]
    print(f"Total virtual weekly explanation notes found: {len(weekly_explanations)}")
    
    print("\nFirst 10 weekly explanations details:")
    for idx, row in weekly_explanations.head(10).iterrows():
        date_val = str(row['Día'])
        name_val = str(row['Name']).encode('ascii', errors='replace').decode('ascii')
        text_preview = str(row['IntervalsText'])[:100].replace('\n', ' ')
        text_ascii = text_preview.encode('ascii', errors='replace').decode('ascii')
        
        print(f"\nRow {idx} | Date: {date_val}")
        print(f"Title/Name: {name_val}")
        print(f"Body: {repr(text_ascii)}...")
        
        # Check ordering on that day
        same_day_all = df[df['Día'] == row['Día']]
        print(f"Ordering on {date_val}:")
        for sub_idx, sub_row in same_day_all.iterrows():
            sub_name = str(sub_row['Name']).encode('ascii', errors='replace').decode('ascii')
            sub_sport = str(sub_row['SportType']).encode('ascii', errors='replace').decode('ascii')
            sub_cat = str(sub_row['Category']).encode('ascii', errors='replace').decode('ascii')
            print(f"  [{sub_cat}] - Name: {sub_name} - Sport: {sub_sport}")

if __name__ == "__main__":
    test_notes()
