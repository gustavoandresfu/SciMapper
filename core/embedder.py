"""
AutoSMS Framework - Módulo de Embeddings (Embedder)
Gestiona la selección de modelos de lenguaje por dominio,
vectorización semántica densa y caché de vectores binarios.
"""

import os
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

class AutoEmbedder:
    def __init__(self, config: dict):
        self.config = config
        self.nlp_cfg = config.get("nlp_tuning", {})
        self.output_dir = config.get("project_metadata", {}).get("output_dir", "./output")

        # Determinar modelo según preset o selección personalizada
        preset = self.nlp_cfg.get("domain_preset", "software_engineering")
        catalog = self.nlp_cfg.get("domain_presets_catalog", {})
        self.model_name = catalog.get(preset, self.nlp_cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))
        self.cache_file = os.path.join(self.output_dir, "embeddings_cache.npy")

    def encode(self, df: pd.DataFrame) -> np.ndarray:
        print(f"\n🧠 GENERACIÓN DE EMBEDDINGS DENSOS...")
        print(f"   Modelo seleccionado: {self.model_name}")

        textos = (df["title"] + ". " + df["abstract"]).tolist()

        if os.path.exists(self.cache_file):
            print(f"   ⚡ Cargando vectores precalculados desde caché: {self.cache_file}")
            embeddings = np.load(self.cache_file)
            if len(embeddings) == len(textos):
                return embeddings
            print("   [!] Caché desactualizada, recalculando...")

        print(f"   Iniciando inferencia semántica sobre {len(textos)} documentos...")
        model = SentenceTransformer(self.model_name)
        embeddings = model.encode(textos, show_progress_bar=True, batch_size=32, normalize_embeddings=True)

        np.save(self.cache_file, embeddings)
        print(f"   💾 Vectores guardados exitosamente ({embeddings.shape[0]} docs, {embeddings.shape[1]} dims).")
        return embeddings
