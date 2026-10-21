"""
AutoSMS Framework - Módulo de Selección Estratificada (Selector)
==============================================================
Identifica de forma algorítmica los artículos candidatos más representativos
para la Discusión Cualitativa Profunda mediante:
1. Umbral inteligente de citas mínimas (prioriza papers con validación bibliométrica).
2. Centralidad semántica respecto al centroide del cluster (medoide).
3. Impacto de citas normalizado logarítmicamente.
4. Cobertura proporcional balanceada por cada una de las taxonomías activas.
"""

import os
import json
import numpy as np
import pandas as pd

class AutoSelector:
    def __init__(self, config: dict):
        self.config = config
        self.output_dir = config.get("project_metadata", {}).get("output_dir", "./output")
        self.synth_cfg = config.get("qualitative_synthesis", {})
        self.top_per_topic = self.synth_cfg.get("candidates_per_topic", 3)
        self.min_citations = self.synth_cfg.get("min_citations", 1)

    def select_candidates(self, df: pd.DataFrame, embeddings: np.ndarray, topics_info: dict) -> list:
        print("\n🎯 SELECCIÓN ESTRATIFICADA DE ARTÍCULOS PARA LA DISCUSIÓN...")
        print(f"   Estrategia: Centralidad Semántica (60%) + Citas (40%) | Umbral preferente: >= {self.min_citations} citas")

        candidates_list = []

        # Asegurar tipos y columnas
        df["topic_id"] = df["topic_id"].astype(int)
        df["cited_by_count"] = pd.to_numeric(df.get("cited_by_count", 0), errors="coerce").fillna(0).astype(int)

        for tid_str, t_info in topics_info.items():
            tid = int(tid_str)
            if t_info.get("exclude_prisma", False):
                print(f"   [!] Omitiendo Tópico {tid} (marcado como excluido en PRISMA).")
                continue

            indices = df.index[df["topic_id"] == tid].tolist()
            if not indices:
                continue

            sub_embs = embeddings[indices]
            sub_df = df.loc[indices].copy()

            # 1. Calcular centroide semántico del cluster
            centroid = np.mean(sub_embs, axis=0)
            centroid_norm = np.linalg.norm(centroid) + 1e-9

            # 2. Similaridad Coseno con el centroide (Centralidad)
            sub_norms = np.linalg.norm(sub_embs, axis=1) + 1e-9
            cos_sim = np.dot(sub_embs, centroid) / (sub_norms * centroid_norm)
            sim_min, sim_max = cos_sim.min(), cos_sim.max()
            sim_scaled = (cos_sim - sim_min) / (sim_max - sim_min + 1e-9)

            # 3. Impacto de Citas normalizado logarítmicamente
            cites = sub_df["cited_by_count"].values
            cite_log = np.log1p(cites)
            cite_min, cite_max = cite_log.min(), cite_log.max()
            cite_scaled = (cite_log - cite_min) / (cite_max - cite_min + 1e-9)

            # 4. Puntuación combinada multiobjetivo
            composite_score = (0.60 * sim_scaled) + (0.40 * cite_scaled)
            sub_df["score_representatividad"] = np.round(composite_score, 4)
            sub_df["centralidad_semantica"] = np.round(cos_sim, 4)

            # 5. Filtro inteligente de citas mínimas:
            # Si existen papers en este cluster con >= min_citations, se les da prioridad
            has_cited_papers = (sub_df["cited_by_count"] >= self.min_citations).any()
            sub_df["meets_citation_threshold"] = sub_df["cited_by_count"] >= self.min_citations

            if has_cited_papers:
                # Priorizar primero los que superan el umbral de citas, luego por score
                sorted_candidates = sub_df.sort_values(
                    by=["meets_citation_threshold", "score_representatividad"],
                    ascending=[False, False]
                ).head(self.top_per_topic)
            else:
                # Si todos tienen 0 citas (ej. cluster 100% de 2025/2026), ordenar puramente por score
                sorted_candidates = sub_df.sort_values(by="score_representatividad", ascending=False).head(self.top_per_topic)

            for rank, (_, row) in enumerate(sorted_candidates.iterrows()):
                is_preselected = (rank == 0)
                n_cites = int(row["cited_by_count"])
                
                if n_cites >= self.min_citations:
                    notes = f"✔ Validación bibliométrica confirmada ({n_cites} citas)."
                else:
                    notes = "⚠️ Sin citas acumuladas (publicación reciente/early access). Validar aporte cualitativo."

                candidates_list.append({
                    "topic_id": tid,
                    "topic_name": t_info.get("assigned_name", f"Tópico {tid}"),
                    "rank_in_topic": rank + 1,
                    "selected_for_deep_review": is_preselected,
                    "title": str(row["title"]),
                    "authors": str(row["authors"]),
                    "publication_year": int(row["publication_year"]) if str(row["publication_year"]).isdigit() else 2024,
                    "venue": str(row["venue"]),
                    "cited_by_count": n_cites,
                    "doi": str(row["doi"]),
                    "centrality_score": float(row["centralidad_semantica"]),
                    "composite_score": float(row["score_representatividad"]),
                    "meets_citation_threshold": bool(row["meets_citation_threshold"]),
                    "abstract": str(row["abstract"]),
                    "human_notes": notes
                })

        # Guardar en JSON (para edición humana)
        json_out = os.path.join(self.output_dir, "candidatos_discusion.json")
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(candidates_list, f, indent=2, ensure_ascii=False)

        # Guardar también en CSV (para lectura en Excel)
        csv_out = os.path.join(self.output_dir, "candidatos_discusion.csv")
        export_df = pd.DataFrame(candidates_list).drop(columns=["abstract"])
        export_df.to_csv(csv_out, index=False, encoding="utf-8-sig")

        print(f"✔ Lista de candidatos sugeridos generada ({len(candidates_list)} artículos evaluados):")
        print(f"   JSON editable: {json_out}")
        print(f"   CSV resumido:  {csv_out}")
        print("💡 Abre 'candidatos_discusion.json' y ajusta 'selected_for_deep_review': true/false según tu criterio.")
        return candidates_list
