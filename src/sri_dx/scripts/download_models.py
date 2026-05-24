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
    logger.info("Starting model downloads...")

    # 1. Embeddings model (Bi-Encoder)
    logger.info(f"Downloading Bi-Encoder: {MODELS['embeddings']}...")
    AutoTokenizer.from_pretrained(MODELS["embeddings"])
    AutoModel.from_pretrained(MODELS["embeddings"])

    # 2. Re-ranking models (Cross-Encoders)
    logger.info(f"Downloading Cross-Encoders...")
    CrossEncoder(MODELS["reranking_fast"])
    CrossEncoder(MODELS["reranking_precise"])

    # 3. Semantic Chunking model
    logger.info(f"Downloading Semantic Chunking model: {MODELS['semantic_chunking']}...")
    SentenceTransformer(MODELS["semantic_chunking"])

    # 4. NER model (Clinical Entities)
    logger.info(f"Downloading NER pipeline: {MODELS['ner']}...")
    pipeline("ner", model=MODELS["ner"])

    logger.info("All models have been downloaded and stored in the local cache.")

if __name__ == "__main__":
    main()
