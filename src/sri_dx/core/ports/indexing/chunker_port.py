from abc import ABC, abstractmethod
from typing import List, Optional
from sri_dx.core.schemas.indexing.chunk_config import ChunkingConfig
from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument
from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument

class ChunkerPort(ABC):
    """
    Puerto para estrategias de chunking.
    Permite cambiar algoritmos sin afectar al sistema.
    """
    
    @abstractmethod
    def chunk_document(
        self, 
        document: AcquiredDocument, 
        config: Optional[ChunkingConfig] = None
    ) -> List[ChunkDocument]:
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
        documents: List[AcquiredDocument], 
        config: Optional[ChunkingConfig] = None
    ) -> List[List[ChunkDocument]]:
        """
        Procesa múltiples documentos en lote.
        
        Returns:
            Lista de listas de chunks (preserva orden)
        """
        

    @abstractmethod
    def chunk_strategy(self) -> str:
        """
        Nombre de la estrategia de chunking utilizada.
        """
        