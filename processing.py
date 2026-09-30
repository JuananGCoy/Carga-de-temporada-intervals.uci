import pandas as pd
import re
from datetime import datetime
from workout_converter import convert_to_intervals_format

def parse_spanish_date(date_str):
    if pd.isna(date_str):
        return None
        
    date_str = str(date_str).strip().lower()
    
    # Regex to match spanish dates "miércoles, 22 de abril de 2026"
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    match = re.search(r'(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})', date_str)
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        year = int(match.group(3))
        if month_str in meses:
            month = meses[month_str]
            return f"{year:04d}-{month:02d}-{day:02d}"
            
    # Fallback to standard pandas parser
    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def sanitize_workout_text(text):
    if not text:
        return ""
        
    lines = str(text).split('\n')
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # Detectar multiplicadores de series: ej. "6x", "4x", "10x", "3 x"
        is_multiplier = re.match(r'^\d+\s*[xX]\s*$', line_stripped)
        
        if is_multiplier:
            # Añadir la línea de repetición (ej. "6x")
            cleaned_lines.append(line_stripped)
            
            # Buscar pasos de la serie saltándose líneas vacías
            steps = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_line_stripped = next_line.strip()
                
                # Omitir líneas vacías
                if not next_line_stripped:
                    j += 1
                    continue
                
                # Si empieza por "-", es un paso de entrenamiento
                if next_line_stripped.startswith("-"):
                    # Asegurar la sangría de 2 espacios
                    steps.append(f"  {next_line_stripped}")
                    j += 1
                else:
                    # Fin de la serie
                    break
            
            cleaned_lines.extend(steps)
            i = j
        else:
            cleaned_lines.append(line)
            i += 1
            
    return '\n'.join(cleaned_lines)

def map_sport_name(text):
    if not text:
        return 'Workout'
    text_lower = str(text).lower().strip()
    
    # Mapeo de términos habituales en español a la nomenclatura oficial de Intervals.icu
    mapping = {
        'Swim': ["natación", "natacion", "piscina", "swim", "swimming", "agua abierta"],
        'Ride': ["bici", "rodillo", "ciclismo", "bicicleta", "ride", "cycling", "bike"],
        'Run': ["carrera", "correr", "run", "running"],
        'WeightTraining': ["gimnasio", "fuerza", "gym", "pesas", "weighttraining", "core", "mantenimiento"]
    }
    
    for sport, keywords in mapping.items():
        for kw in keywords:
            if kw in text_lower:
                return sport
                
    return 'Workout' # Fallback estándar

def split_double_sessions_dynamic(df):
    new_rows = []
    
    # Disciplinas para detectar dobles sesiones en texto
    sports_map = {
        "Natación": "Swim",
        "Carrera": "Run",
        "Bici": "Ride",
        "Bicicleta": "Ride",
        "Gimnasio": "WeightTraining",
        "Fuerza": "WeightTraining",
        "Rodillo": "Ride",
        "GYM": "WeightTraining",
        ".GYM": "WeightTraining",
        "Gym": "WeightTraining"
    }
    
    for idx, row in df.iterrows():
        workout_text = str(row.get('IntervalsText', ''))
        text_lower = workout_text.lower()
        
        # Si ya se ha asignado un SportType en el Excel (no es nulo o vacío)
        excel_sport = row.get('SportType')
        if pd.notna(excel_sport) and excel_sport != '' and excel_sport is not None:
            new_row = row.copy()
            # Si no tiene Category asignada, la asignamos según el texto
            if pd.isna(new_row.get('Category')) or new_row.get('Category') == '':
                new_row['Category'] = assign_category(workout_text)
            new_rows.append(new_row)
            continue
            
        # De lo contrario, intentamos dividir dobles sesiones o autodetectar por texto
        found_keywords = [kw for kw in sports_map.keys() if kw.lower() + ":" in text_lower]
        
        if "transición" in text_lower or "transicion" in text_lower:
            if ":" in workout_text:
                content = workout_text.split(":", 1)[1]
            else:
                content = workout_text
                
            sub_sessions = content.split("+")
            for sub in sub_sessions:
                sub = sub.strip()
                if not sub: continue
                new_row = row.copy()
                new_row['IntervalsText'] = sub
                new_row['SportType'] = assign_sport(sub)
                new_row['Category'] = assign_category(sub)
                new_rows.append(new_row)
        elif len(found_keywords) > 1:
            pattern = r"(?i)(Natación:|Carrera:|Bici:|Bicicleta:|Gimnasio:|Fuerza:|Rodillo:|\.GYM:|GYM:|Gym:)"
            splits = re.split(pattern, workout_text)
            
            for i in range(1, len(splits), 2):
                header = splits[i]
                content = splits[i+1] if i+1 < len(splits) else ""
                block_text = f"{header}{content}".strip()
                
                new_row = row.copy()
                new_row['IntervalsText'] = block_text
                new_row['SportType'] = assign_sport(header)
                new_row['Category'] = assign_category(block_text)
                new_rows.append(new_row)
        else:
            new_row = row.copy()
            new_row['SportType'] = assign_sport(workout_text)
            new_row['Category'] = assign_category(workout_text)
            new_rows.append(new_row)
            
    return pd.DataFrame(new_rows)

def split_double_sessions_by_columns(df):
    new_rows = []
    session_suffixes = ['', '2', '3', '4']
    
    for idx, row in df.iterrows():
        created_for_row = 0
        
        for suffix in session_suffixes:
            text_key = f'IntervalsText{suffix}' if suffix else 'IntervalsText'
            sport_key = f'SportType{suffix}' if suffix else 'SportType'
            name_key = f'Name{suffix}' if suffix else 'Name'
            
            text_val = str(row.get(text_key, '')).strip() if text_key in row else ''
            has_text = text_val and text_val.lower() != 'nan' and text_val != ''
            
            if has_text:
                sport_val = row.get(sport_key)
                if pd.isna(sport_val) or str(sport_val).strip() == '' or str(sport_val).strip().lower() == 'nan':
                    sport_val = assign_sport(text_val)
                else:
                    sport_val = map_sport_name(sport_val)
                    
                name_val = row.get(name_key)
                if pd.isna(name_val) or str(name_val).strip() == '' or str(name_val).strip().lower() == 'nan':
                    name_val = None
                    
                row_new = row.copy()
                row_new['IntervalsText'] = text_val
                row_new['SportType'] = sport_val
                row_new['Name'] = name_val
                row_new['Category'] = assign_category(text_val) if (pd.isna(row_new.get('Category')) or str(row_new.get('Category')).strip() in ['', 'nan']) else row_new.get('Category')
                new_rows.append(row_new)
                created_for_row += 1
                
        if created_for_row == 0:
            row_empty = row.copy()
            row_empty['IntervalsText'] = ''
            row_empty['SportType'] = 'Workout'
            row_empty['Name'] = None
            row_empty['Category'] = 'WORKOUT'
            new_rows.append(row_empty)
            
    res_df = pd.DataFrame(new_rows)
    cols_to_drop = [c for c in res_df.columns if c.startswith('IntervalsText') or c.startswith('SportType') or c.startswith('Name')]
    for keep_col in ['IntervalsText', 'SportType', 'Name']:
        if keep_col in cols_to_drop:
            cols_to_drop.remove(keep_col)
            
    return res_df.drop(columns=cols_to_drop, errors='ignore')

def assign_sport(text):
    text_lower = text.lower()
    
    sports = {
        'Swim': ["natación", "natacion", "piscina", "swim", "swimming", "crol", "metros"],
        'Run': ["carrera", "correr", "run", "running", "pace"],
        'Ride': ["bici", "rodillo", "ciclismo", "bicicleta", "ride", "cycling", "bike", "rpm", "watts", "watios", "cadencia"],
        'WeightTraining': ["gimnasio", "fuerza", "gym", "pesas", "weighttraining", "core", "movilidad"]
    }
    
    best_sport = 'Workout'
    min_index = float('inf')
    
    for sport, keywords in sports.items():
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx != -1 and idx < min_index:
                min_index = idx
                best_sport = sport
                
    return best_sport

def assign_category(text):
    text_lower = str(text).lower()
    if "competición" in text_lower or "competicion" in text_lower or "triatlón" in text_lower or "triatlon" in text_lower or "quebrantahuesos" in text_lower:
        return 'RACE_A'
    if "descanso" in text_lower or "nota" in text_lower or "vacaciones" in text_lower:
        return 'NOTE'
    return 'WORKOUT'

def map_category_name(text):
    if not text:
        return 'WORKOUT'
    text_lower = str(text).lower().strip()
    if "race_a" in text_lower or "competicion" in text_lower or "competición" in text_lower:
        return 'RACE_A'
    if "race_b" in text_lower:
        return 'RACE_B'
    if "race_c" in text_lower:
        return 'RACE_C'
    if "note" in text_lower or "nota" in text_lower or "descanso" in text_lower:
        return 'NOTE'
    return 'WORKOUT'

def parse_daily_explanation(text):
    text_str = str(text).strip()
    if not text_str:
        return None
        
    objective = "Objetivo día"
    body = text_str
    
    # Expresión regular para Lógica / Logica, soportando la ó con tilde
    logica_pattern = r'(?i)L?[oó]gica\s*:'
    
    if "objetivo" in text_str.lower() and re.search(logica_pattern, text_str):
        parts = re.split(logica_pattern, text_str, maxsplit=1)
        if len(parts) > 1:
            logica_part = parts[1].strip()
            objetivo_part = parts[0].strip()
            
            # Limpiar el prefijo "Objetivo:"
            obj_sub_match = re.sub(r'(?i)^Objetivos?\s*:\s*', '', objetivo_part).strip()
            if obj_sub_match:
                objective = obj_sub_match
            body = f"Objetivo: {objective}\n\nLógica: {logica_part}"
            
            objective = objective.replace('\n', ' ').strip()
            if len(objective) > 100:
                objective = objective[:97] + "..."
    else:
        lines = [line.strip() for line in text_str.split('\n') if line.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) < 60 and any(k in first_line.lower() for k in ["contexto", "objetivo", "día", "dia", "bloque"]):
                objective = first_line
                body = text_str
            else:
                objective = "Objetivo día"
                body = text_str
                
    return {
        "name": objective,
        "description": body
    }

def process_excel(file_upload, sheet_name=None, column_mapping=None):
    """
    Procesa un archivo Excel cargado.
    Permite especificar la hoja de cálculo (sheet_name) y un diccionario column_mapping
    que indica qué columnas del Excel corresponden a cada dato que necesitamos:
    - 'Día' (Fecha, requerido)
    - 'IntervalsText' (Texto del entrenamiento, requerido)
    - 'SportType' (Deporte, opcional)
    - 'Name' (Nombre del entrenamiento, opcional)
    - 'Category' (Categoría, opcional)
    - 'ExplicacionSemana' (Explicación de la semana, opcional)
    """
    if sheet_name:
        df = pd.read_excel(file_upload, sheet_name=sheet_name)
    else:
        df = pd.read_excel(file_upload)
        
    if column_mapping is None:
        # Default mapping fallback
        column_mapping = {
            'Día': 'Día',
            'IntervalsText': 'Entrenamiento principal',
            'SportType': None,
            'Name': None,
            'Category': None,
            'ExplicacionSemana': None
        }
        for standard, default_val in [('Día', 'Día'), ('IntervalsText', 'Entrenamiento principal'), ('ExplicacionSemana', 'Explicación semana')]:
            if default_val in df.columns:
                column_mapping[standard] = default_val
            else:
                for col in df.columns:
                    col_str = str(col).lower()
                    if standard.lower() in col_str or default_val.lower() in col_str or (standard == 'ExplicacionSemana' and 'explicac' in col_str):
                        column_mapping[standard] = col
                        break
    else:
        # Asegurar compatibilidad si se pasa mapping incompleto
        if 'ExplicacionSemana' not in column_mapping:
            column_mapping['ExplicacionSemana'] = None
            for col in df.columns:
                col_str = str(col).lower()
                if 'explicación' in col_str or 'explicacion' in col_str:
                    column_mapping['ExplicacionSemana'] = col
                    break
                        
    # Renombrar columnas según el mapping del usuario
    reverse_mapping = {}
    for standard_key, excel_col in column_mapping.items():
        if excel_col and excel_col in df.columns:
            reverse_mapping[excel_col] = standard_key
            
    df = df.rename(columns=reverse_mapping)
    
    # Nos aseguramos de tener la columna 'Día'
    if 'Día' not in df.columns:
        return pd.DataFrame()
        
    # Parsear fechas de Día
    df['Día'] = df['Día'].apply(parse_spanish_date)
    
    # Nos quedamos solo con las filas que tienen una fecha válida
    df = df.dropna(subset=['Día'])
    
    # Extraer las explicaciones semanales virtuales antes de dividir dobles sesiones
    virtual_rows = []
    if 'ExplicacionSemana' in df.columns:
        seen_dates = set()
        for idx, row in df.iterrows():
            exp_text = row['ExplicacionSemana']
            date_val = row['Día']
            if pd.notna(exp_text) and str(exp_text).strip() != "" and date_val and date_val not in seen_dates:
                parsed = parse_daily_explanation(exp_text)
                if parsed:
                    seen_dates.add(date_val)
                    note_name = parsed['name']
                    if not note_name.startswith("Objetivo"):
                        note_name = f"Objetivo: {note_name}"
                    virtual_rows.append({
                        'Día': date_val,
                        'IntervalsText': parsed['description'],
                        'SportType': 'Workout',
                        'Name': note_name,
                        'Category': 'NOTE',
                        'Status': '✅ Listo'
                    })
        df = df.drop(columns=['ExplicacionSemana'])
    
    # Inicializar columnas requeridas si no se mapearon
    if 'IntervalsText' not in df.columns:
        df['IntervalsText'] = ''
    else:
        df['IntervalsText'] = df['IntervalsText'].fillna('').apply(sanitize_workout_text)
        
    for suffix in ['', '2', '3', '4']:
        t_col = f'IntervalsText{suffix}' if suffix else 'IntervalsText'
        s_col = f'SportType{suffix}' if suffix else 'SportType'
        n_col = f'Name{suffix}' if suffix else 'Name'
        
        if t_col in df.columns:
            df[t_col] = df[t_col].fillna('').apply(sanitize_workout_text)
        if s_col in df.columns:
            df[s_col] = df[s_col].fillna('').apply(map_sport_name)
        else:
            df[s_col] = None
        if n_col not in df.columns:
            df[n_col] = None
        
    if 'Category' in df.columns:
        df['Category'] = df['Category'].fillna('').apply(map_category_name)
    else:
        df['Category'] = None
        
    # Split dobles/múltiples sesiones y autodetectar deportes
    has_multi_cols = any(f'IntervalsText{s}' in df.columns for s in ['2', '3', '4'])
    if has_multi_cols:
        df = split_double_sessions_by_columns(df)
    else:
        df = split_double_sessions_dynamic(df)
    
    # Aplicar conversión local a formato Intervals.icu si el texto no está ya estructurado
    def apply_conversion(row):
        text = str(row.get('IntervalsText', '')).strip()
        category = row.get('Category', 'WORKOUT')
        sport = row.get('SportType', 'Workout')
        
        if category != 'NOTE' and text:
            t_lower = text.lower()
            is_structured = ('warmup' in t_lower or 'main set' in t_lower or 'cooldown' in t_lower or text.startswith('-'))
            if not is_structured:
                return convert_to_intervals_format(text, sport)
        return text

    if 'IntervalsText' in df.columns:
        df['IntervalsText'] = df.apply(apply_conversion, axis=1)
    
    # Concatenar notas semanales virtuales
    if virtual_rows:
        virtual_df = pd.DataFrame(virtual_rows)
        # Sincronizar columnas
        for col in df.columns:
            if col not in virtual_df.columns:
                virtual_df[col] = None
        for col in virtual_df.columns:
            if col not in df.columns:
                df[col] = None
        df = pd.concat([df, virtual_df], ignore_index=True)
        
        # Ordenar: Día cronológicamente, y que NOTE vaya primero
        df['_sort_priority'] = df['Category'].apply(lambda x: 0 if x == 'NOTE' else 1)
        df = df.sort_values(by=['Día', '_sort_priority'], kind='mergesort').reset_index(drop=True)
        df = df.drop(columns=['_sort_priority'])
    
    # Limpieza final
    df['Status'] = '✅ Listo'
    df['Category'] = df['Category'].apply(lambda x: x if pd.notna(x) and x != '' else 'WORKOUT')
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df
