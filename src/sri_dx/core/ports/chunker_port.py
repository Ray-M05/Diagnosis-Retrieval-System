from abc import ABC, abstractmethod
from typing import List, Optional
from ..schemas.chunk_schema import Chunk, ChunkingConfig
from ..schemas.schema import Document

class ChunkerPort(ABC):
    """
    Puerto para estrategias de chunking.
    Permite cambiar algoritmos sin afectar al sistema.
    """
    
    @abstractmethod
    def chunk_document(
        self, 
        document: Document, 
        config: Optional[ChunkingConfig] = None
    ) -> List[Chunk]:
        """
        Divide un documento en chunks.
        
        Args:
            document: Documento a dividir
            config: Configuración de chunking (tamaño, overlap, etc.)
            
        Returns:
            Lista de chunks con metadatos
        """
        

    @abstractmethod
    def chunk_batch(
        self, 
        documents: List[Document], 
        config: Optional[ChunkingConfig] = None
    ) -> List[List[Chunk]]:
        """
        Procesa múltiples documentos en lote.
        
        Returns:
            Lista de listas de chunks (preserva orden)
        """
        

    @abstractmethod
    def chunk_strategy(self) -> Chunk:
        """
        Procesa un único documento utilizando la estrategia de chunking definida.
        """
        