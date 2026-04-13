# core/ports/embedding_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray

from sri_dx.core.schemas.indexing.embedding_config import EmbeddingConfig

class EmbeddingPort(ABC):
    """
    Puerto para modelos de embeddings.
    Permite cambiar modelos sin modificar pipeline.
    """
    
    @abstractmethod
    def encode(
        self, 
        texts: List[str], 
        config: Optional[EmbeddingConfig] = None
    ) -> "NDArray[Any]":
        """
        Genera embeddings para una lista de textos.
        
        Args:
            texts: Textos a vectorizar
            config: Configuración (normalización, dimensionalidad, etc.)
            
        Returns:
            Array numpy de shape (len(texts), embedding_dim)
        """
        

    @abstractmethod
    def encode_query(
        self, 
        query: str, 
        config: Optional[EmbeddingConfig] = None
    ) -> "NDArray[Any]":
        """
        Genera embedding para query (puede tener tratamiento especial).
        
        Returns:
            Vector numpy de shape (embedding_dim,)
        """
        

    