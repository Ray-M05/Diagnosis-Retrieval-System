# core/ports/indexing/entity_extractor_port.py
"""Puerto para estrategias de extracción de entidades clínicas."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from sri_dx.core.schemas.indexing.entity_schema import (
    ClinicalEntity,
    EntityExtractionConfig,
)


class EntityExtractorPort(ABC):
    """
    Puerto para estrategias de extracción de entidades clínicas.
    
    Permite cambiar el modelo/estrategia sin afectar al pipeline.
    Implementaciones posibles:
    - Bio_ClinicalBERT (NER)
    - ScispaCy
    - Diccionario + reglas
    - LLM-based extraction
    """
    
    @abstractmethod
    def extract(
        self, 
        text: str, 
        config: Optional[EntityExtractionConfig] = None
    ) -> List[ClinicalEntity]:
        """
        Extrae entidades clínicas de un texto.
        
        Args:
            text: Texto clínico a procesar
            config: Configuración de extracción
            
        Returns:
            Lista de entidades encontradas con sus metadatos
        """
    
    @abstractmethod
    def extract_batch(
        self, 
        texts: List[str], 
        config: Optional[EntityExtractionConfig] = None
    ) -> List[List[ClinicalEntity]]:
        """
        Extrae entidades de múltiples textos (optimizado para GPU/batching).
        
        Args:
            texts: Lista de textos a procesar
            config: Configuración de extracción
            
        Returns:
            Lista de listas de entidades (preserva orden)
        """
    
    @abstractmethod
    def get_supported_labels(self) -> List[str]:
        """
        Retorna los tipos de entidades que este extractor puede identificar.
        
        Returns:
            Lista de labels soportados. Ej: ['PROBLEM', 'TREATMENT', 'TEST']
        """
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nombre/identificador del modelo usado."""
