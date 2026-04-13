# adapters/embeddings/clinical_bert_adapter.py
"""
Adaptador para Bio_ClinicalBERT.

Este adaptador encapsula el modelo de HuggingFace para que los módulos
no dependan directamente de `transformers`. Proporciona:
- Carga lazy del modelo (solo cuando se necesita)
- Singleton pattern para reusar el modelo
- Embeddings de oraciones/textos
- Tokenización optimizada
- Aceleración ONNX Runtime en CPU (2-4x más rápido)
- FP16 en GPU CUDA

Modelo: emilyalsentzer/Bio_ClinicalBERT
- Entrenado en MIMIC-III (notas clínicas reales)
- Ideal para: diagnósticos, procedimientos, registros de pacientes
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    import torch
    from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)


from .schemas.clinical_bert_config import ClinicalBERTConfig

# Directorio para cachear el modelo ONNX exportado
_ONNX_CACHE_DIR = Path.home() / ".cache" / "sri_dx" / "onnx"


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
        self._onnx_session = None  # onnxruntime.InferenceSession si se usa ONNX
        self._using_onnx = False

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

    def _get_onnx_path(self) -> Path:
        """Retorna la ruta donde se cachea el modelo ONNX exportado."""
        safe_name = self.config.model_name.replace("/", "_")
        return _ONNX_CACHE_DIR / f"{safe_name}.onnx"

    def _export_to_onnx(self) -> Path:
        """Exporta el modelo PyTorch a formato ONNX (una sola vez, cacheado)."""
        import torch

        onnx_path = self._get_onnx_path()
        if onnx_path.exists():
            logger.info("Modelo ONNX cacheado encontrado: %s", onnx_path)
            return onnx_path

        logger.info("Exportando modelo a ONNX (una sola vez)...")
        onnx_path.parent.mkdir(parents=True, exist_ok=True)

        # Crear inputs dummy para el export
        dummy_input = self._tokenizer(
            "dummy text for export",
            return_tensors="pt",
            padding="max_length",
            max_length=self.config.max_length,
            truncation=True,
        )

        # Export
        torch.onnx.export(
            self._model,
            (dummy_input["input_ids"], dummy_input["attention_mask"]),
            str(onnx_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "seq"},
                "attention_mask": {0: "batch", 1: "seq"},
                "last_hidden_state": {0: "batch", 1: "seq"},
            },
            opset_version=14,
            do_constant_folding=True,
        )

        logger.info("Modelo ONNX exportado en: %s (%.1f MB)",
                     onnx_path, onnx_path.stat().st_size / (1024 * 1024))
        return onnx_path

    def _create_onnx_session(self, onnx_path: Path) -> None:
        """Crea una InferenceSession de ONNX Runtime con optimizaciones."""
        import onnxruntime as ort

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = 0  # 0 = auto (usa todos los cores)
        sess_options.inter_op_num_threads = 0

        self._onnx_session = ort.InferenceSession(
            str(onnx_path),
            sess_options,
            providers=["CPUExecutionProvider"],
        )

        logger.info("ONNX Runtime session creada (providers: %s)",
                     self._onnx_session.get_providers())

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

        # Prioridad 1: GPU CUDA con FP16
        if self.config.device != "cpu" and torch.cuda.is_available():
            self._model = self._model.to(self.config.device)
            if self.config.use_fp16:
                self._model = self._model.half()
                logger.info("Modelo en FP16 (half precision)")
            torch.backends.cudnn.benchmark = True
            self._model.eval()
            self._loaded = True
            logger.info("Modelo cargado en %s (GPU, batch_size=%d)",
                        self.config.device, self.config.batch_size)
            return

        # Prioridad 2: ONNX Runtime en CPU
        if self.config.use_onnx:
            try:
                import onnxruntime  # noqa: F401
                self._model.eval()
                onnx_path = self._export_to_onnx()
                self._create_onnx_session(onnx_path)
                self._using_onnx = True
                # Liberar modelo PyTorch de memoria (ya no se necesita)
                self._model = None
                import gc
                gc.collect()
                self._loaded = True
                logger.info("Modelo cargado con ONNX Runtime (CPU optimizado, batch_size=%d)",
                            self.config.batch_size)
                return
            except ImportError:
                logger.info("onnxruntime no disponible, usando PyTorch CPU")
            except Exception as e:
                logger.warning("Error al configurar ONNX Runtime: %s. Fallback a PyTorch CPU.", e)

        # Prioridad 3: PyTorch CPU (fallback)
        self._model.eval()
        self._loaded = True
        logger.info("Modelo cargado en CPU (PyTorch, batch_size=%d)", self.config.batch_size)

    def _unload_model(self) -> None:
        """Libera memoria del modelo."""
        self._model = None
        self._tokenizer = None
        self._onnx_session = None
        self._using_onnx = False
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

    def _encode_onnx(self, texts: List[str]) -> "torch.Tensor":
        """Genera embeddings usando ONNX Runtime (CPU optimizado)."""
        import numpy as np
        import torch

        all_embeddings = []

        for i in range(0, len(texts), self.config.batch_size):
            batch_texts = texts[i:i + self.config.batch_size]

            encoded = self._tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
                return_tensors="np",
            )

            input_ids = encoded["input_ids"].astype(np.int64)
            attention_mask = encoded["attention_mask"].astype(np.int64)

            # ONNX Runtime inference
            outputs = self._onnx_session.run(
                ["last_hidden_state"],
                {"input_ids": input_ids, "attention_mask": attention_mask},
            )
            hidden_states = outputs[0]  # (batch, seq_len, 768)

            # Mean pooling en numpy
            mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
            sum_embeddings = np.sum(hidden_states * mask_expanded, axis=1)
            sum_mask = np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            embeddings = sum_embeddings / sum_mask

            all_embeddings.append(embeddings)

        result = np.concatenate(all_embeddings, axis=0)

        # Normalizar
        if self.config.normalize_embeddings:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            norms = np.clip(norms, a_min=1e-9, a_max=None)
            result = result / norms

        return torch.from_numpy(result).float()

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
        self._load_model()

        if isinstance(texts, str):
            texts = [texts]

        # Ruta ONNX Runtime (CPU optimizado)
        if self._using_onnx:
            return self._encode_onnx(texts)

        # Ruta PyTorch (GPU o CPU fallback)
        import torch

        all_embeddings = []

        for i in range(0, len(texts), self.config.batch_size):
            batch_texts = texts[i:i + self.config.batch_size]

            encoded = self._tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
                return_tensors="pt"
            )

            if self.config.device != "cpu":
                encoded = {k: v.to(self.config.device) for k, v in encoded.items()}

            with torch.no_grad():
                outputs = self._model(**encoded)

            embeddings = self._pool_embeddings(
                outputs.last_hidden_state,
                encoded["attention_mask"]
            )

            all_embeddings.append(embeddings)

        result = torch.cat(all_embeddings, dim=0)

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
            return hidden_states[:, 0, :]

        elif self.config.pooling_strategy == "max":
            mask = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
            hidden_states = hidden_states * mask
            hidden_states[mask == 0] = -1e9
            return torch.max(hidden_states, dim=1)[0]

        else:  # mean (default)
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

        emb1 = torch.nn.functional.normalize(emb1, p=2, dim=1)
        emb2 = torch.nn.functional.normalize(emb2, p=2, dim=1)

        return torch.mm(emb1, emb2.T)
