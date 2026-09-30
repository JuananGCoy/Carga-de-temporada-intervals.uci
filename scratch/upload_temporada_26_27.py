import os
import sys
import pandas as pd
import time
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from processing import process_excel, sanitize_workout_text
from intervals_api import upload_to_intervals

def load_config():
    with open("athletes.json", 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    print("Loading config...")
    config = load_config()
    coach_api_key = config.get("coach_api_key", "")
    coach_athlete_id = config.get("coach_athlete_id", "308429")
    
    file_path = "Temporada 26-27.xlsx"
    print(f"Reading {file_path}...")
    df_raw = pd.read_excel(file_path, sheet_name="Entrenamientos")
    
    # Combine Entrenamiento principal and Explicación
    def combine_texts(row):
        ep = row.get('Entrenamiento principal')
        ex = row.get('Explicación')
        
        ep_valid = pd.notna(ep) and str(ep).strip() != ""
        ex_valid = pd.notna(ex) and str(ex).strip() != ""
        
        if ep_valid and ex_valid:
            return f"{str(ex).strip()}\n\n{str(ep).strip()}"
        elif ep_valid:
            return str(ep).strip()
        elif ex_valid:
            return str(ex).strip()
        return ""

    df_raw['CombinedText'] = df_raw.apply(combine_texts, axis=1)
    
    # Save to a temporary excel so process_excel can read it
    temp_excel = "temp_temporada.xlsx"
    df_raw.to_excel(temp_excel, index=False)
    
    mapping = {
        'Día': 'Día',
        'IntervalsText': 'CombinedText',
        'SportType': None,
        'Name': 'Competiciones',
        'Category': 'Categoría',
        'ExplicacionSemana': None
    }
    
    print("Processing excel data...")
    df_processed = process_excel(temp_excel, column_mapping=mapping)
    
    if df_processed.empty:
        print("No valid rows found after processing.")
        return
        
    print(f"Total rows to upload: {len(df_processed)}")
    
    success_count = 0
    fail_count = 0
    
    for idx, row in df_processed.iterrows():
        # filter out empty rows
        if pd.isna(row['Día']) or not str(row['Día']).strip():
            continue
            
        date_str = str(row['Día']).strip()
        iso_date = f"{date_str}T08:00:00"
        
        # Determine name
        name_val = row.get('Name')
        if pd.notna(name_val) and str(name_val).strip() != "":
            workout_name = str(name_val).strip()
        else:
            workout_name = f"{row['SportType']} - {date_str}"
            
        payload = {
            "start_date_local": iso_date,
            "type": row['SportType'],
            "category": row.get('Category', 'WORKOUT'),
            "name": workout_name,
            "workout_text": sanitize_workout_text(row['IntervalsText'])
        }
        
        print(f"[{idx+1}/{len(df_processed)}] Uploading {date_str} - {workout_name} - {row['SportType']}")
        
        success, msg = upload_to_intervals(
            athlete_id=coach_athlete_id,
            api_key=coach_api_key,
            payload=payload,
            use_athlete_key=True # uploading to own account (juanan)
        )
        
        if success:
            success_count += 1
        else:
            print(f"  -> ERROR: {msg}")
            fail_count += 1
            
        time.sleep(0.5) # Rate limiting
        
    print(f"\n--- UPLOAD SUMMARY ---")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    
    # cleanup temp file
    if os.path.exists(temp_excel):
        os.remove(temp_excel)

if __name__ == "__main__":
    main()
