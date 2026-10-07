"""Memory-light replacement for sentence-transformers (no PyTorch).

Runs the same all-MiniLM-L6-v2 model through ONNX Runtime via `fastembed`. Exposes the small part of the
SentenceTransformer API this project uses: .encode(str | list[str], convert_to_numpy=..., normalize_embeddings=...).
"""
import logging
import os
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger('ats_resume_scorer')


def _default_cache_dir() -> str:
    # Same folder at build time and at run time, so the model is downloaded once (not on every cold start).
    return os.getenv('EMBEDDER_CACHE_DIR', os.path.join(os.getcwd(), '.cache', 'fastembed'))


class OnnxEmbedder:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_dir: Optional[str] = None, threads: int = 1):
        from fastembed import TextEmbedding          # imported lazily: keeps `import backend.*` cheap

        if '/' not in model_name:                    # "all-MiniLM-L6-v2" -> "sentence-transformers/all-MiniLM-L6-v2"
            model_name = f'sentence-transformers/{model_name}'
        self.model_name = model_name
        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=cache_dir or _default_cache_dir(),
            threads=threads,
        )

    def encode(
        self,
        sentences: Union[str, List[str]],
        convert_to_tensor: bool = False,             # accepted for API compatibility; always returns numpy
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = False,          # embeddings are always L2-normalised (as in all-MiniLM-L6-v2)
        batch_size: int = 32,
        show_progress_bar: bool = False,
        **_ignored,
    ) -> np.ndarray:
        single = isinstance(sentences, str)
        texts = [sentences] if single else [str(s) for s in sentences]
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)

        vecs = np.asarray(list(self._model.embed(texts, batch_size=batch_size)), dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.clip(norms, 1e-12, None)
        return vecs[0] if single else vecs
