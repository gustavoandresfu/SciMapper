"""
AutoSMS Framework - Módulo de Embeddings (Embedder)
Gestiona la selección de modelos de lenguaje por dominio,
vectorización semántica densa y caché de vectores binarios.
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("scimapper.embedder")

class AutoEmbedder:
    def __init__(self, config: dict):
        self.config = config
        self.nlp_cfg = config.get("nlp_tuning", {})
        self.output_dir = config.get("project_metadata", {}).get("output_dir", "./output")
        os.makedirs(self.output_dir, exist_ok=True)

        # Determinar modelo según preset o selección personalizada
        preset = self.nlp_cfg.get("domain_preset", "software_engineering")
        catalog = self.nlp_cfg.get("domain_presets_catalog", {})
        self.model_name = catalog.get(preset, self.nlp_cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))
        model_slug = hashlib.sha256(self.model_name.encode()).hexdigest()[:8]
        self.cache_file = os.path.join(self.output_dir, f"embeddings_cache_{model_slug}.npy")
        self.meta_file = os.path.join(self.output_dir, f"embeddings_cache_{model_slug}.json")

    def _cache_valid(self, n_texts: int) -> bool:
        if not (os.path.exists(self.cache_file) and os.path.exists(self.meta_file)):
            return False
        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("model_name") != self.model_name:
                return False
            if meta.get("n_texts") != n_texts:
                return False
            arr = np.load(self.cache_file)
            if arr.shape[0] != n_texts:
                return False
            return True
        except Exception:
            return False

    def encode(self, df: pd.DataFrame) -> np.ndarray:
        logger.info("GENERACIÓN DE EMBEDDINGS DENSOS...")
        logger.info("Modelo seleccionado: %s", self.model_name)

        textos = (df["title"] + ". " + df["abstract"]).tolist()

        if self._cache_valid(len(textos)):
            logger.info("Cargando vectores precalculados desde caché: %s", self.cache_file)
            return np.load(self.cache_file)

        logger.info("Iniciando inferencia semántica sobre %d documentos...", len(textos))
        model = SentenceTransformer(self.model_name)
        embeddings = model.encode(textos, show_progress_bar=True, batch_size=32, normalize_embeddings=True)

        np.save(self.cache_file, embeddings)
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(
                {"model_name": self.model_name, "n_texts": len(textos), "shape": list(embeddings.shape)},
                f, indent=2, ensure_ascii=False,
            )
        logger.info("Vectores guardados (%d docs, %d dims).", embeddings.shape[0], embeddings.shape[1])
        return embeddings
