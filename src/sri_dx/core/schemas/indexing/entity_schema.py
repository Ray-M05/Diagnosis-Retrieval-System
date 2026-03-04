# core/schemas/indexing/entity_schema.py
"""Schemas para extracción de entidades clínicas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class ClinicalEntity:
    """Entidad clínica extraída del texto."""
    
    text: str
    """Texto original de la entidad."""
    
    label: str
    """Tipo de entidad: PROBLEM, TREATMENT, TEST, ANATOMY, etc."""
    
    start_char: int
    """Posición inicial en el texto original."""
    
    end_char: int
    """Posición final en el texto original."""
    
    confidence: float
    """Score de confianza [0.0, 1.0]."""
    
    normalized_text: Optional[str] = None
    """Texto normalizado (lowercase, sin acentos, etc.)."""
    
    umls_cui: Optional[str] = None
    """Código UMLS si se pudo mapear."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Metadatos adicionales específicos del extractor."""


@dataclass
class EntityExtractionConfig:
    """Configuración para extracción de entidades."""
    
    labels_to_extract: Optional[List[str]] = None
    """Si None, extrae todas. Ej: ['PROBLEM', 'TREATMENT']"""
    
    min_confidence: float = 0.5
    """Umbral mínimo de confianza."""
    
    batch_size: int = 8
    """Tamaño de batch para procesamiento."""
    
    max_length: int = 512
    """Longitud máxima de secuencia en tokens."""
    
    overlap_tokens: int = 64
    """Overlap para documentos largos (sliding window)."""
