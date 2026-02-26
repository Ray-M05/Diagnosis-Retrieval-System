import sys
import os

def check_health():
    print("SRI-DX Health Check")
    print("-" * 20)
    
    # Check for pyproject.toml
    if os.path.exists("pyproject.toml"):
        print("[OK] pyproject.toml encontrado")
    else:
        print("[FAIL] pyproject.toml no encontrado")
        
    # Check for core modules
    if os.path.exists("src/sri_dx/core/schemas.py"):
        print("[OK] Core schemas disponibles")
    else:
        print("[FAIL] Core schemas no encontrados")
        
    print("-" * 20)
    print("Verificación completada.")

if __name__ == "__main__":
    check_health()
