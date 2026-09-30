import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from processing import process_excel

def verify():
    print("Testing processing.py...")
    excel_path = "Planificación temporada 25-26.xlsx"
    sheet_name = "Entrenos"
    
    mapping = {
        'Día': 'Día',
        'IntervalsText': 'Entrenamiento principal',
        'SportType': None, # Let it autodetect
        'Name': None,
        'Category': None
    }
    
    try:
        df = process_excel(excel_path, sheet_name=sheet_name, column_mapping=mapping)
        print("Success! Processed DataFrame shape:", df.shape)
        print("\nColumns in processed DataFrame:", list(df.columns))
        print("\nFirst 5 rows of data:")
        for idx, row in df.head(5).iterrows():
            status_clean = str(row['Status']).replace("✅", "[OK]")
            date_val = str(row['Día'])
            sport_val = str(row['SportType'])
            cat_val = str(row['Category'])
            text_preview = str(row['IntervalsText'])[:100].replace('\n', ' ')
            
            # Remove non-ascii characters for clean console print
            text_ascii = text_preview.encode('ascii', errors='replace').decode('ascii')
            
            print(f"Row {idx}: Date={date_val}, Sport={sport_val}, Category={cat_val}, Status={status_clean}")
            print(f"  Text: {repr(text_ascii)}...")
    except Exception as e:
        print("ERROR running verification:", e)
        import traceback
        traceback.printexc()

if __name__ == "__main__":
    verify()
