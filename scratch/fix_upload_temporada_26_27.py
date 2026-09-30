import os
import sys
import pandas as pd
import time
import requests
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from processing import process_excel
from ai_agent import process_workout_text
from intervals_api import upload_to_intervals

def load_config():
    with open("athletes.json", 'r', encoding='utf-8') as f:
        return json.load(f)

from dotenv import load_dotenv

def clear_events(athlete_id, api_key, start_date, end_date):
    print(f"Clearing existing events between {start_date} and {end_date}...")
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/events?oldest={start_date}&newest={end_date}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    # try Basic Auth first, then Bearer if it fails, as in intervals_api
    res = requests.get(url, auth=('API_KEY', api_key), headers={"Accept": "application/json"})
    if res.status_code == 403:
        res = requests.get(url, headers=headers)
        
    if res.status_code != 200:
        print(f"Failed to fetch events: {res.status_code} - {res.text}")
        return

    events = res.json()
    print(f"Found {len(events)} events. Deleting...")
    for ev in events:
        ev_id = ev.get("id")
        if ev_id:
            del_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/events/{ev_id}"
            d_res = requests.delete(del_url, auth=('API_KEY', api_key))
            if d_res.status_code == 403:
                d_res = requests.delete(del_url, headers=headers)
            if d_res.status_code != 200:
                print(f"Failed to delete event {ev_id}: {d_res.status_code}")
            time.sleep(0.2)
    print("Clearing complete.")

def main():
    load_dotenv()
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    
    config = load_config()
    coach_api_key = config.get("coach_api_key", "")
    coach_athlete_id = config.get("coach_athlete_id", "308429")
    
    # 1. Clear previous bad uploads
    clear_events(coach_athlete_id, coach_api_key, "2026-07-13", "2026-11-30")
    
    file_path = "Temporada 26-27.xlsx"
    df_raw = pd.read_excel(file_path, sheet_name="Entrenamientos")
    
    mapping = {
        'Día': 'Día',
        'IntervalsText': 'Entrenamiento principal',
        'ExplicacionSemana': 'Explicación',
        'Category': 'Categoría',
        'Name': 'Competiciones',
        'SportType': None
    }
    
    df_processed = process_excel(file_path, sheet_name="Entrenamientos", column_mapping=mapping)
    
    success_count = 0
    fail_count = 0
    
    for idx, row in df_processed.iterrows():
        if pd.isna(row['Día']) or not str(row['Día']).strip():
            continue
            
        date_str = str(row['Día']).strip()
        iso_date = f"{date_str}T08:00:00"
        
        name_val = row.get('Name')
        if pd.notna(name_val) and str(name_val).strip() != "":
            workout_name = str(name_val).strip()
        else:
            workout_name = f"{row['SportType']} - {date_str}"
            
        category = row.get('Category', 'WORKOUT')
        original_text = str(row['IntervalsText'])
        
        # Determine final text to upload
        if category == 'NOTE':
            # Notes don't need AI translation
            final_text = original_text
        else:
            print(f"[{idx+1}/{len(df_processed)}] AI Formatting: {date_str} - {row['SportType']}...")
            final_text = process_workout_text(gemini_api_key, row['SportType'], original_text)
            if "ERROR_AI_FAILED" in final_text:
                print(f"  -> AI Failed for row {idx}. Using original text.")
                final_text = original_text
                
        payload = {
            "start_date_local": iso_date,
            "type": row['SportType'],
            "category": category,
            "name": workout_name,
            "workout_text": final_text
        }
        
        print(f"[{idx+1}/{len(df_processed)}] Uploading {date_str} - {workout_name} - {category}")
        
        success, msg = upload_to_intervals(
            athlete_id=coach_athlete_id,
            api_key=coach_api_key,
            payload=payload,
            use_athlete_key=True
        )
        
        if success:
            success_count += 1
        else:
            print(f"  -> ERROR: {msg}")
            fail_count += 1
            
        time.sleep(0.5)
        
    print(f"\n--- UPLOAD SUMMARY ---")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    main()
