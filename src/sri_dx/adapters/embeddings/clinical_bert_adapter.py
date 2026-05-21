# adapters/embeddings/clinical_bert_adapter.py
"""
Adapter for Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT).

Provides lazy loading, singleton reuse, and optional ONNX Runtime
acceleration on CPU (2-4x faster than PyTorch). Falls back to PyTorch
CPU when ONNX Runtime is unavailable, and uses FP16 on CUDA when available.
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

_ONNX_CACHE_DIR = Path.home() / ".cache" / "sri_dx" / "onnx"


class ClinicalBERTAdapter:
    """Singleton adapter for Bio_ClinicalBERT."""

    _instance: Optional["ClinicalBERTAdapter"] = None
    _model: Optional["AutoModel"] = None
    _tokenizer: Optional["AutoTokenizer"] = None

    def __init__(self, config: Optional[ClinicalBERTConfig] = None):
        self.config = config or ClinicalBERTConfig()
        self._loaded = False
        self._onnx_session = None  # onnxruntime.InferenceSession si se usa ONNX
        self._using_onnx = False

    @classmethod
    def get_instance(cls, config: Optional[ClinicalBERTConfig] = None) -> "ClinicalBERTAdapter":
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets the singleton — useful in tests."""
        if cls._instance is not None:
            cls._instance._unload_model()
        cls._instance = None

    def _get_onnx_path(self) -> Path:
        safe_name = self.config.model_name.replace("/", "_")
        return _ONNX_CACHE_DIR / f"{safe_name}.onnx"

    def _export_to_onnx(self) -> Path:
        """Exports the PyTorch model to ONNX format once and caches it."""
        import torch

        onnx_path = self._get_onnx_path()
        if onnx_path.exists():
            logger.info("Cached ONNX model found: %s", onnx_path)
            return onnx_path

        logger.info("Exporting model to ONNX (one-time operation)...")
        onnx_path.parent.mkdir(parents=True, exist_ok=True)

        dummy_input = self._tokenizer(
            "dummy text for export",
            return_tensors="pt",
            padding="max_length",
            max_length=self.config.max_length,
            truncation=True,
        )

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

        logger.info("ONNX model exported: %s (%.1f MB)",
                     onnx_path, onnx_path.stat().st_size / (1024 * 1024))
        return onnx_path

    def _create_onnx_session(self, onnx_path: Path) -> None:
        import onnxruntime as ort

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = 0  # 0 = auto (all available cores)
        sess_options.inter_op_num_threads = 0

        self._onnx_session = ort.InferenceSession(
            str(onnx_path),
            sess_options,
            providers=["CPUExecutionProvider"],
        )

        logger.info("ONNX Runtime session created (providers: %s)",
                     self._onnx_session.get_providers())

    def _load_model(self) -> None:
        if self._loaded:
            return

        logger.info("Loading model %s...", self.config.model_name)

        import torch
        from transformers import AutoModel, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self._model = AutoModel.from_pretrained(self.config.model_name)

        if self.config.device != "cpu" and torch.cuda.is_available():
            self._model = self._model.to(self.config.device)
            if self.config.use_fp16:
                self._model = self._model.half()
                logger.info("Model loaded in FP16 (half precision)")
            torch.backends.cudnn.benchmark = True
            self._model.eval()
            self._loaded = True
            logger.info("Model loaded on %s (GPU, batch_size=%d)",
                        self.config.device, self.config.batch_size)
            return

        if self.config.use_onnx:
            try:
                import onnxruntime  # noqa: F401
                self._model.eval()
                onnx_path = self._export_to_onnx()
                self._create_onnx_session(onnx_path)
                self._using_onnx = True
                self._model = None
                import gc
                gc.collect()
                self._loaded = True
                logger.info("Model loaded with ONNX Runtime (CPU-optimized, batch_size=%d)",
                            self.config.batch_size)
                return
            except ImportError:
                logger.info("onnxruntime not available, falling back to PyTorch CPU")
            except Exception as e:
                logger.warning("ONNX Runtime setup failed: %s. Falling back to PyTorch CPU.", e)

        self._model.eval()
        self._loaded = True
        logger.info("Model loaded on CPU (PyTorch, batch_size=%d)", self.config.batch_size)

    def _unload_model(self) -> None:
        self._model = None
        self._tokenizer = None
        self._onnx_session = None
        self._using_onnx = False
        self._loaded = False

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    @property
    def tokenizer(self) -> "AutoTokenizer":
        self._load_model()
        return self._tokenizer

    @property
    def model(self) -> "AutoModel":
        self._load_model()
        return self._model

    def _encode_onnx(self, texts: List[str]) -> "torch.Tensor":
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

            outputs = self._onnx_session.run(
                ["last_hidden_state"],
                {"input_ids": input_ids, "attention_mask": attention_mask},
            )
            hidden_states = outputs[0]

            mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
            sum_embeddings = np.sum(hidden_states * mask_expanded, axis=1)
            sum_mask = np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            embeddings = sum_embeddings / sum_mask

            all_embeddings.append(embeddings)

        result = np.concatenate(all_embeddings, axis=0)

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
        """Returns embeddings for one or more texts. Shape: (n_texts, 768)."""
        self._load_model()

        if isinstance(texts, str):
            texts = [texts]

        if self._using_onnx:
            return self._encode_onnx(texts)

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
        self._load_model()
        return self._tokenizer.tokenize(text)

    def get_embedding_dim(self) -> int:
        """Returns 768 (BERT-base hidden size)."""
        return 768

    def similarity(
        self,
        text1: Union[str, List[str]],
        text2: Union[str, List[str]]
    ) -> "torch.Tensor":
        import torch

        emb1 = self.encode(text1)
        emb2 = self.encode(text2)

        emb1 = torch.nn.functional.normalize(emb1, p=2, dim=1)
        emb2 = torch.nn.functional.normalize(emb2, p=2, dim=1)

        return torch.mm(emb1, emb2.T)
