def build_indexes():
    print("Iniciando construcción de índices...")
    print("1. Cargando corpus desde data/sample/")
    print("2. Generando embeddings (Sentence Transformers)")
    print("3. Construyendo índice ANN (HNSW)")
    print("4. Guardando artefactos en data/artifacts/")
    print("¡Índices construidos con éxito!")

if __name__ == "__main__":
    build_indexes()
