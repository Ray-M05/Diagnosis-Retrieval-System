#!/usr/bin/env python3
"""
Script de verificación del sistema SRI-DX
Verifica que Elasticsearch esté disponible y el entorno esté correctamente configurado.
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def check_elasticsearch():
    """Verifica la conexión con Elasticsearch"""
    es_host = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    max_retries = 5
    retry_delay = 2
    
    print(f"🔍 Verificando conexión con Elasticsearch en {es_host}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(f"{es_host}/_cluster/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                status = health.get("status", "unknown")
                
                status_emoji = {
                    "green": "✅",
                    "yellow": "⚠️",
                    "red": "❌"
                }.get(status, "❓")
                
                print(f"{status_emoji} Elasticsearch está disponible!")
                print(f"   Estado del cluster: {status}")
                print(f"   Nodos: {health.get('number_of_nodes', 'N/A')}")
                print(f"   Shards activos: {health.get('active_shards', 'N/A')}")
                return True
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                print(f"⏳ Intento {attempt}/{max_retries} - Esperando {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print("❌ No se pudo conectar con Elasticsearch")
                print(f"   Verifica que el servicio esté corriendo en {es_host}")
                return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False
    
    return False

def check_environment():
    """Verifica las variables de entorno necesarias"""
    print("\n🔧 Verificando configuración del entorno...")
    
    required_vars = [
        "ELASTICSEARCH_HOST",
        "ELASTICSEARCH_INDEX",
        "EMBEDDING_MODEL_NAME",
        "DATA_DIR"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: NO CONFIGURADA")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Variables faltantes: {', '.join(missing_vars)}")
        print("   Revisa tu archivo .env")
        return False
    
    return True

def check_data_dir():
    """Verifica que el directorio de datos exista"""
    print("\n📁 Verificando directorio de datos...")
    
    data_dir = os.getenv("DATA_DIR", "./data")
    
    if os.path.exists(data_dir):
        print(f"   ✅ Directorio '{data_dir}' existe")
        
        # Verificar subdirectorios importantes
        subdirs = ["raw", "processed", "artifacts"]
        for subdir in subdirs:
            path = os.path.join(data_dir, subdir)
            if os.path.exists(path):
                print(f"      ✅ {subdir}/")
            else:
                print(f"      📝 {subdir}/ (se creará cuando sea necesario)")
        return True
    else:
        print(f"   ⚠️  Directorio '{data_dir}' no existe (se creará automáticamente)")
        return True

def check_index_exists():
    """Verifica si el índice de Elasticsearch existe"""
    print("\n📊 Verificando índice de Elasticsearch...")
    
    es_host = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    index_name = os.getenv("ELASTICSEARCH_INDEX", "sri_dx_diagnoses")
    
    try:
        response = requests.get(f"{es_host}/{index_name}", timeout=5)
        if response.status_code == 200:
            index_info = response.json()
            doc_count_response = requests.get(f"{es_host}/{index_name}/_count", timeout=5)
            doc_count = doc_count_response.json().get("count", 0)
            
            print(f"   ✅ Índice '{index_name}' existe")
            print(f"   📄 Documentos indexados: {doc_count}")
            return True
        elif response.status_code == 404:
            print(f"   📝 Índice '{index_name}' no existe (será creado al indexar)")
            return True
        else:
            print(f"   ⚠️  Estado inesperado: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ⚠️  No se pudo verificar (Elasticsearch no disponible)")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("🏥 SRI-DX - Verificación del Sistema")
    print("=" * 60)
    
    checks = [
        ("Variables de entorno", check_environment),
        ("Elasticsearch", check_elasticsearch),
        ("Directorio de datos", check_data_dir),
        ("Índice de Elasticsearch", check_index_exists),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ OK" if result else "❌ FALLO"
        print(f"{status:10} - {name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 ¡Todo está configurado correctamente!")
        print("\nPuedes iniciar la aplicación con:")
        print("   docker compose up")
        print("   o")
        print("   uv run streamlit run src/sri_dx/app/ui_streamlit.py")
        return 0
    else:
        print("\n⚠️  Hay problemas que resolver antes de continuar")
        print("\nRevisa la documentación en README.md")
        return 1

if __name__ == "__main__":
    sys.exit(main())
