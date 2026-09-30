import re

def parse_weekly_explanation(text):
    text_str = str(text).strip()
    if not text_str:
        return None
        
    objective = "Objetivo de la semana"
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
            if len(first_line) < 60 and any(k in first_line.lower() for k in ["contexto", "objetivo", "semana", "bloque"]):
                objective = first_line
                body = text_str
            else:
                objective = "Explicación de la semana"
                body = text_str
                
    return {
        "name": objective,
        "description": body
    }

def run_tests():
    # Test 1: New format
    new_format = """Objetivo: Llegar al 100% de frescura y clavar la estrategia en Albacete.

Lógica: Lunes rodaje suave de soltura, miércoles un estímulo mínimo para activar el sistema neuromuscular y viernes descanso total."""
    
    res1 = parse_weekly_explanation(new_format)
    print("Test 1 (New Format):")
    print("  Name:", repr(res1["name"]))
    print("  Desc starts with:", repr(res1["description"][:100]))
    
    # Test 2: Old format
    old_format = """CONTEXTO DE LA SEMANA
Seguimos en BASE-3, con el foco ya puesto en la intensidad controlada..."""
    res2 = parse_weekly_explanation(old_format)
    print("\nTest 2 (Old Format):")
    print("  Name:", repr(res2["name"]))
    print("  Desc starts with:", repr(res2["description"][:100]))

if __name__ == "__main__":
    run_tests()
