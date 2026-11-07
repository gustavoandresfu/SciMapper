"""
AutoSMS Framework - Módulo de Clustering, c-TF-IDF y Dinámica Temporal
=====================================================================
Ejecuta la reducción bidimensional (PCA + t-SNE), agrupamiento semántico,
extracción formal de palabras clave diferenciales (c-TF-IDF) y el cálculo
del Radar de Madurez Temporal (CAGR y clasificación de tendencias).
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer

logger = logging.getLogger("scimapper.clusterer")

class AutoClusterer:
    def __init__(self, config: dict):
        self.config = config
        self.nlp_cfg = config.get("nlp_tuning", {})
        self.output_dir = config.get("project_metadata", {}).get("output_dir", "./output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.k = self.nlp_cfg.get("n_clusters", 6)

    def reduce_2d(self, embeddings: np.ndarray) -> np.ndarray:
        n_samples = embeddings.shape[0]
        if n_samples <= 2:
            return np.zeros((n_samples, 2))

        method = str(self.nlp_cfg.get("dimensionality_reduction", "pca_tsne")).lower()
        if method == "pca" or n_samples < 8:
            logger.info("Reduciendo dimensionalidad con PCA (modo ligero)...")
            n_components = min(2, embeddings.shape[1], max(1, n_samples - 1))
            pca = PCA(n_components=n_components, random_state=42)
            coords = pca.fit_transform(embeddings)
            if coords.shape[1] == 1:
                coords = np.column_stack([coords, np.zeros(n_samples)])
            return coords

        logger.info("Reduciendo dimensionalidad a espacio bidimensional (PCA + t-SNE)...")

        pca_dims = min(50, embeddings.shape[1], n_samples - 1)
        pca = PCA(n_components=pca_dims, random_state=42)
        pca_feats = pca.fit_transform(embeddings)

        perp = min(30, max(2, (n_samples - 1) // 3))
        tsne = TSNE(n_components=2, perplexity=perp, learning_rate="auto", init="pca", random_state=42)
        coords = tsne.fit_transform(pca_feats)
        return coords

    def cluster(self, embeddings: np.ndarray) -> np.ndarray:
        n_samples = embeddings.shape[0]
        actual_k = min(self.k, max(1, n_samples // 2))
        logger.info("Ejecutando agrupamiento no supervisado en k=%d clusters...", actual_k)
        if actual_k <= 1:
            return np.zeros(n_samples, dtype=int)
        kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        return labels

    def extract_c_tf_idf(self, texts: list, labels: np.ndarray, top_n: int = 8) -> dict:
        logger.info("Calculando Class-based TF-IDF (c-TF-IDF) para extraccion lexica...")
        unique_labels = sorted(list(set(labels)))
        docs_per_cluster = []
        for l in unique_labels:
            cluster_docs = [texts[i] for i in range(len(texts)) if labels[i] == l]
            docs_per_cluster.append(" ".join(cluster_docs))

        stop_words = self.nlp_cfg.get("stop_words", "english")
        if isinstance(stop_words, str) and stop_words.lower() in ("none", "null", ""):
            stop_words = None

        vec = CountVectorizer(ngram_range=(1, 2), stop_words=stop_words, min_df=1, max_df=1.0)
        X = vec.fit_transform(docs_per_cluster)
        words = vec.get_feature_names_out()

        tf = X.toarray().astype(float)
        w_sum = tf.sum(axis=1, keepdims=True)
        tf_norm = tf / np.maximum(w_sum, 1)

        # IDF clásico por documento (cluster): log(1 + N / (df + 1))
        doc_freq = (tf > 0).sum(axis=0).astype(float)
        n_clusters = max(1, len(docs_per_cluster))
        idf = np.log(1.0 + (n_clusters / (doc_freq + 1.0)))
        c_tf_idf = tf_norm * idf

        keywords_dict = {}
        for idx, l in enumerate(unique_labels):
            top_idx = np.argsort(c_tf_idf[idx])[::-1][:top_n]
            top_words = [words[i] for i in top_idx if len(words[i]) > 2]
            keywords_dict[int(l)] = top_words

        return keywords_dict

    def compute_temporal_dynamics(self, df: pd.DataFrame, labels: np.ndarray) -> dict:
        logger.info("Calculando Radar de Madurez Temporal y CAGR por Topico...")
        dynamics = {}
        unique_labels = sorted(list(set(labels)))

        # Convertir años a enteros válidos
        years_series = pd.to_numeric(df["publication_year"], errors="coerce").dropna()
        if years_series.empty:
            min_year, max_year = 2018, 2026
        else:
            min_year, max_year = int(years_series.min()), int(years_series.max())

        span = max(1, max_year - min_year)

        for l in unique_labels:
            sub = df[df["topic_id"] == l]
            sub_years = pd.to_numeric(sub["publication_year"], errors="coerce").dropna().astype(int)

            yearly_counts = {}
            for y in range(min_year, max_year + 1):
                yearly_counts[y] = int((sub_years == y).sum())

            # Cálculo de CAGR suavizado (Laplace +1 para evitar ceros)
            start_val = yearly_counts.get(min_year, 0) + yearly_counts.get(min_year + 1, 0)
            end_val = yearly_counts.get(max_year, 0) + yearly_counts.get(max_year - 1, 0)
            
            cagr = ((end_val + 1.0) / (start_val + 1.0)) ** (1.0 / max(1, span - 1)) - 1.0
            cagr_pct = round(cagr * 100, 1)

            # Proporción de producción en los últimos 3 años
            recent_years = [max_year, max_year - 1, max_year - 2]
            recent_count = sum(yearly_counts.get(y, 0) for y in recent_years)
            recent_ratio = round((recent_count / max(1, len(sub))) * 100, 1)

            # Clasificación de la dinámica
            if cagr_pct >= 12.0 or recent_ratio >= 45.0:
                category = "Emergente (Hot Topic)"
                badge = "🚀 Emergente"
            elif cagr_pct <= -8.0 and recent_ratio <= 22.0:
                category = "En Declive"
                badge = "📉 En Declive"
            else:
                category = "Maduro / Consolidado"
                badge = "⚖️ Maduro"

            dynamics[int(l)] = {
                "cagr_percent": cagr_pct,
                "recent_ratio_percent": recent_ratio,
                "trend_category": category,
                "badge": badge,
                "yearly_distribution": yearly_counts
            }

        return dynamics

    def run(self, df: pd.DataFrame, embeddings: np.ndarray) -> tuple:
        df = df.reset_index(drop=True).copy()
        coords = self.reduce_2d(embeddings)
        df["coord_x"] = coords[:, 0]
        df["coord_y"] = coords[:, 1]

        labels = self.cluster(embeddings)
        df["topic_id"] = labels

        texts = (df["title"] + ". " + df["abstract"]).tolist()
        keywords = self.extract_c_tf_idf(texts, labels, top_n=8)
        temporal_info = self.compute_temporal_dynamics(df, labels)

        # Generar JSON de tópicos descubiertos enriquecido
        topics_summary = {}
        for l in sorted(keywords.keys()):
            sub = df[df["topic_id"] == l]
            sample_titles = sub["title"].head(4).tolist()
            t_dyn = temporal_info.get(l, {})

            topics_summary[l] = {
                "count": len(sub),
                "percentage": round(len(sub) / len(df) * 100, 1),
                "keywords": keywords[l],
                "sample_titles": sample_titles,
                "assigned_name": f"Tópico {l}: {', '.join(keywords[l][:3]).title()}",
                "exclude_prisma": False,
                "temporal_dynamics": t_dyn
            }

        topics_json_path = os.path.join(self.output_dir, "discovered_topics.json")
        with open(topics_json_path, "w", encoding="utf-8") as f:
            json.dump(topics_summary, f, indent=2, ensure_ascii=False)

        logger.info("Archivo de ajuste humano generado en: %s", topics_json_path)
        return df, topics_summary
