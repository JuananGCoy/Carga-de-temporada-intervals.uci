import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from processing import sanitize_workout_text

def test_sanitize():
    bad_input = """Warmup

- 10m Z1 Pace

Main Set

6x

- 2m Z3 Pace

- 2m Z2 Pace

Cooldown

- 6m Z1 Pace"""

    print("--- INPUT CON ERRORES ---")
    print(repr(bad_input))
    
    cleaned = sanitize_workout_text(bad_input)
    
    print("\n--- OUTPUT SANITIZADO ---")
    print(cleaned)

if __name__ == "__main__":
    test_sanitize()
