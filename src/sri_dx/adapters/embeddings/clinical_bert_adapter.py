# adapters/embeddings/clinical_bert_adapter.py
"""
Adaptador para Bio_ClinicalBERT.

Este adaptador encapsula el modelo de HuggingFace para que los módulos
no dependan directamente de `transformers`. Proporciona:
- Carga lazy del modelo (solo cuando se necesita)
- Singleton pattern para reusar el modelo
- Embeddings de oraciones/textos
- Tokenización optimizada

Modelo: emilyalsentzer/Bio_ClinicalBERT
- Entrenado en MIMIC-III (notas clínicas reales)
- Ideal para: diagnósticos, procedimientos, registros de pacientes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    import torch
    from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClinicalBERTConfig:
    """Configuración del adaptador Bio_ClinicalBERT."""
    
    model_name: str = "emilyalsentzer/Bio_ClinicalBERT"
    """Nombre del modelo en HuggingFace Hub."""
    
    max_length: int = 512
    """Longitud máxima de secuencia en tokens."""
    
    batch_size: int = 16
    """Tamaño de batch para inferencia."""
    
    device: str = "cpu"
    """Dispositivo: 'cpu', 'cuda', 'cuda:0', etc."""
    
    pooling_strategy: str = "mean"
    """Estrategia de pooling: 'mean', 'cls', 'max'."""
    
    normalize_embeddings: bool = True
    """Si True, normaliza embeddings a norma unitaria."""


class ClinicalBERTAdapter:
    """
    Adaptador singleton para Bio_ClinicalBERT.
    
    Uso:
        adapter = ClinicalBERTAdapter.get_instance()
        embeddings = adapter.encode(["texto 1", "texto 2"])
    """
    
    _instance: Optional["ClinicalBERTAdapter"] = None
    _model: Optional["AutoModel"] = None
    _tokenizer: Optional["AutoTokenizer"] = None
    
    def __init__(self, config: Optional[ClinicalBERTConfig] = None):
        """
        Inicializa el adaptador. Usa get_instance() para singleton.
        
        Args:
            config: Configuración del modelo. Si None, usa defaults.
        """
        self.config = config or ClinicalBERTConfig()
        self._loaded = False
    
    @classmethod
    def get_instance(cls, config: Optional[ClinicalBERTConfig] = None) -> "ClinicalBERTAdapter":
        """
        Obtiene instancia singleton del adaptador.
        
        Args:
            config: Configuración (solo se usa en primera llamada)
            
        Returns:
            Instancia compartida del adaptador
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Resetea el singleton (útil para tests)."""
        if cls._instance is not None:
            cls._instance._unload_model()
        cls._instance = None
    
    def _load_model(self) -> None:
        """Carga el modelo de forma lazy."""
        if self._loaded:
            return
        
        logger.info(f"Cargando modelo {self.config.model_name}...")
        
        # Import lazy para no requerir transformers al importar el módulo
        import torch
        from transformers import AutoModel, AutoTokenizer
        
        self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self._model = AutoModel.from_pretrained(self.config.model_name)
        
        # Mover a dispositivo
        if self.config.device != "cpu" and torch.cuda.is_available():
            self._model = self._model.to(self.config.device)
        
        # Modo evaluación (desactiva dropout)
        self._model.eval()
        self._loaded = True
        
        logger.info(f"Modelo cargado en {self.config.device}")
    
    def _unload_model(self) -> None:
        """Libera memoria del modelo."""
        self._model = None
        self._tokenizer = None
        self._loaded = False
        
        # Intentar liberar memoria GPU
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
    
    @property
    def tokenizer(self) -> "AutoTokenizer":
        """Acceso al tokenizer (carga lazy)."""
        self._load_model()
        return self._tokenizer
    
    @property
    def model(self) -> "AutoModel":
        """Acceso al modelo (carga lazy)."""
        self._load_model()
        return self._model
    
    def encode(
        self, 
        texts: Union[str, List[str]], 
        show_progress: bool = False
    ) -> "torch.Tensor":
        """
        Genera embeddings para uno o más textos.
        
        Args:
            texts: Texto único o lista de textos
            show_progress: Mostrar barra de progreso
            
        Returns:
            Tensor de shape (n_texts, embedding_dim) - 768 para BERT
        """
        import torch
        
        self._load_model()
        
        if isinstance(texts, str):
            texts = [texts]
        
        all_embeddings = []
        
        # Procesar en batches
        for i in range(0, len(texts), self.config.batch_size):
            batch_texts = texts[i:i + self.config.batch_size]
            
            # Tokenizar
            encoded = self._tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
                return_tensors="pt"
            )
            
            # Mover a dispositivo
            if self.config.device != "cpu":
                encoded = {k: v.to(self.config.device) for k, v in encoded.items()}
            
            # Forward pass sin gradientes
            with torch.no_grad():
                outputs = self._model(**encoded)
            
            # Pooling
            embeddings = self._pool_embeddings(
                outputs.last_hidden_state, 
                encoded["attention_mask"]
            )
            
            all_embeddings.append(embeddings)
        
        # Concatenar batches
        result = torch.cat(all_embeddings, dim=0)
        
        # Normalizar si está configurado
        if self.config.normalize_embeddings:
            result = torch.nn.functional.normalize(result, p=2, dim=1)
        
        return result.cpu()
    
    def _pool_embeddings(
        self, 
        hidden_states: "torch.Tensor", 
        attention_mask: "torch.Tensor"
    ) -> "torch.Tensor":
        """
        Aplica estrategia de pooling a las representaciones.
        
        Args:
            hidden_states: (batch, seq_len, hidden_dim)
            attention_mask: (batch, seq_len)
            
        Returns:
            (batch, hidden_dim)
        """
        import torch
        
        if self.config.pooling_strategy == "cls":
            # Usar token [CLS]
            return hidden_states[:, 0, :]
        
        elif self.config.pooling_strategy == "max":
            # Max pooling sobre tokens no-padding
            mask = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
            hidden_states = hidden_states * mask
            hidden_states[mask == 0] = -1e9
            return torch.max(hidden_states, dim=1)[0]
        
        else:  # mean (default)
            # Mean pooling sobre tokens no-padding
            mask = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
            sum_embeddings = torch.sum(hidden_states * mask, dim=1)
            sum_mask = torch.clamp(mask.sum(dim=1), min=1e-9)
            return sum_embeddings / sum_mask
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokeniza texto y retorna los tokens como strings.
        
        Args:
            text: Texto a tokenizar
            
        Returns:
            Lista de tokens
        """
        self._load_model()
        return self._tokenizer.tokenize(text)
    
    def get_embedding_dim(self) -> int:
        """Retorna la dimensión de los embeddings (768 para BERT-base)."""
        return 768
    
    def similarity(
        self, 
        text1: Union[str, List[str]], 
        text2: Union[str, List[str]]
    ) -> "torch.Tensor":
        """
        Calcula similitud coseno entre textos.
        
        Args:
            text1: Texto(s) de referencia
            text2: Texto(s) a comparar
            
        Returns:
            Tensor de similitudes
        """
        import torch
        
        emb1 = self.encode(text1)
        emb2 = self.encode(text2)
        
        # Asegurar que estén normalizados
        emb1 = torch.nn.functional.normalize(emb1, p=2, dim=1)
        emb2 = torch.nn.functional.normalize(emb2, p=2, dim=1)
        
        # Similitud coseno = producto punto de vectores normalizados
        return torch.mm(emb1, emb2.T)
