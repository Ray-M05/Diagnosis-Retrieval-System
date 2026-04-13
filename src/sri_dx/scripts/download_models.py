# src/sri_dx/scripts/download_models.py
"""
Script para pre-descargar todos los modelos de Hugging Face usados en el proyecto.
Útil para entornos con conectividad limitada o para asegurar que el sistema 
esté listo para usar offline.
"""

import logging
from transformers import AutoModel, AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sentence_transformers import SentenceTransformer, CrossEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ModelDownloader")

MODELS = {
    "embeddings": "emilyalsentzer/Bio_ClinicalBERT",
    "reranking_fast": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "reranking_precise": "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "semantic_chunking": "sentence-transformers/all-MiniLM-L6-v2",
    "ner": "d4data/biomedical-ner-all"
}

def main():
    logger.info("Iniciando descarga de modelos...")

    # 1. Modelo de Embeddings (Bi-Encoder)
    logger.info(f"Descargando Bi-Encoder: {MODELS['embeddings']}...")
    AutoTokenizer.from_pretrained(MODELS["embeddings"])
    AutoModel.from_pretrained(MODELS["embeddings"])

    # 2. Modelos de Re-ranking (Cross-Encoders)
    logger.info(f"Descargando Cross-Encoders...")
    CrossEncoder(MODELS["reranking_fast"])
    CrossEncoder(MODELS["reranking_precise"])

    # 3. Modelo de Semantic Chunking
    logger.info(f"Descargando Semantic Chunking: {MODELS['semantic_chunking']}...")
    SentenceTransformer(MODELS["semantic_chunking"])

    # 4. Modelo de NER (Entidades Clínicas)
    logger.info(f"Descargando Pipeline NER: {MODELS['ner']}...")
    pipeline("ner", model=MODELS["ner"])

    logger.info("🎉 Todos los modelos han sido descargados y almacenados en la caché local.")

if __name__ == "__main__":
    main()
