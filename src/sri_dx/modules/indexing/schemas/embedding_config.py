"""Pydantic schemas de configuración para el generador de embeddings.

Estos models se usan dentro de `sri_dx.modules.indexing` para mantener
consistencia con otros `core.schemas` y permitir validación.
"""

from pydantic import BaseModel, Field


class EmbeddingGeneratorConfig(BaseModel):
    """Configuración del generador de embeddings."""

    model_name: str = Field(default="Bio_ClinicalBERT", description="Nombre del modelo")
    model_version: str = Field(default="1.0", description="Versión del modelo")
    embedding_dim: int = Field(default=768, ge=1, description="Dimensión del embedding")
    batch_size: int = Field(default=128, ge=1, description="Batch size para inferencia")
    text_preview_length: int = Field(default=200, ge=0, description="Longitud del preview de texto")
    normalize_vectors: bool = Field(default=True, description="Normalizar vectores después de generar")
    device: str = Field(default="auto", description="Dispositivo: auto, cpu, cuda")
