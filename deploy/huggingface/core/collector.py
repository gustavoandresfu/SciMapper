"""
AutoSMS Framework - Módulo de Recolección (Collector)
Maneja la ingesta agnóstica de literatura académica desde OpenAlex API,
reconstrucción de abstracts y deduplicación basada en DOI y hashes de títulos.
"""

import os
import sys
import json
import time
import re
import logging
import urllib.parse
import urllib.request
import urllib.error
import pandas as pd

logger = logging.getLogger("scimapper.collector")

def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return clean_text(" ".join(word for _, word in word_positions))

def normalize_title(t: str) -> str:
    t = re.sub(r'[^a-zA-Z0-9]', '', str(t).lower())
    return t[:80]

class AutoCollector:
    def __init__(self, config: dict):
        self.config = config
        self.meta = config.get("project_metadata", {})
        self.strategy = config.get("search_strategy", {})
        self.email = self.strategy.get("openalex_email", "researcher@example.com")
        self.year_min, self.year_max = self.meta.get("temporal_window", [2018, 2026])
        self.max_per_query = self.strategy.get("max_results_per_query", 100)
        self.output_dir = self.meta.get("output_dir", "./output")
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_from_openalex(self, query: str, max_retries: int = 3) -> list:
        results = []
        base_url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "filter": f"from_publication_date:{self.year_min}-01-01,to_publication_date:{self.year_max}-12-31,has_abstract:true",
            "per_page": min(50, self.max_per_query),
            "mailto": self.email
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        logger.info("Consultando: %s", query[:60])

        obtained = 0
        page = 1
        while obtained < self.max_per_query:
            page_url = f"{url}&page={page}"
            data = None
            for attempt in range(1, max_retries + 1):
                try:
                    req = urllib.request.Request(page_url, headers={"User-Agent": f"AutoSMS-Framework ({self.email})"})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        retry_after = e.headers.get("Retry-After")
                        try:
                            wait = int(retry_after) if retry_after else (5 * attempt)
                        except (TypeError, ValueError):
                            wait = 5 * attempt
                        logger.warning("HTTP 429 en página %d (intento %d/%d). Esperando %ds...", page, attempt, max_retries, wait)
                        time.sleep(wait)
                    else:
                        wait = 2 ** attempt
                        logger.warning("Error HTTP %s página %d (intento %d/%d). Reintentando en %ds", e.code, page, attempt, max_retries, wait)
                        time.sleep(wait)
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                    wait = 2 ** attempt
                    logger.warning("Error página %d (intento %d/%d): %s. Reintentando en %ds", page, attempt, max_retries, e, wait)
                    time.sleep(wait)
            if data is None:
                logger.error("No se pudo obtener la página %d tras %d intentos. Abortando consulta.", page, max_retries)
                break

            items = data.get("results", [])
            if not items:
                break

            for it in items:
                title = clean_text(it.get("title") or "")
                abstract = reconstruct_abstract(it.get("abstract_inverted_index"))
                if len(title) < 10 or len(abstract) < 80:
                    continue

                authors_list = []
                for a in (it.get("authorships") or []):
                    auth = a.get("author") or {}
                    name = auth.get("display_name")
                    if name:
                        authors_list.append(name)
                authors = "; ".join(authors_list) or "Desconocido"

                loc = it.get("primary_location") or {}
                src = loc.get("source") or {}
                venue = src.get("display_name") or "No especificado"

                results.append({
                    "id": it.get("id", ""),
                    "doi": it.get("doi", "") or "",
                    "title": title,
                    "authors": authors,
                    "publication_year": it.get("publication_year", ""),
                    "venue": venue,
                    "abstract": abstract,
                    "cited_by_count": it.get("cited_by_count", 0)
                })
                obtained += 1
                if obtained >= self.max_per_query:
                    break

            page += 1
            time.sleep(1.0)

        logger.info("✔ %d registros con abstract obtenidos.", len(results))
        return results

    def run(self) -> pd.DataFrame:
        print("\n🚀 INICIANDO RECOLECCIÓN AUTOMATIZADA DE LITERATURA...")
        all_records = []
        queries = self.strategy.get("queries", [])
        for i, q in enumerate(queries):
            if i > 0:
                time.sleep(1.0)
            recs = self.fetch_from_openalex(q)
            all_records.extend(recs)

        # Deduplicación
        seen = set()
        unique_records = []
        for r in all_records:
            doi = r["doi"].strip().lower()
            norm_t = normalize_title(r["title"])
            key = doi if (doi and len(doi) > 5) else norm_t
            if key and key not in seen:
                seen.add(key)
                unique_records.append(r)

        df = pd.DataFrame(unique_records)
        out_csv = os.path.join(self.output_dir, "corpus_candidatos.csv")
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")

        print(f"\n=======================================================")
        print(f"📊 REPORTE DE RECOLECCIÓN:")
        print(f"   Total registros brutos:       {len(all_records)}")
        print(f"   Registros únicos filtrados:   {len(df)}")
        print(f"   Duplicados removidos:         {len(all_records) - len(df)}")
        print(f"   Archivo guardado en:          {out_csv}")
        print(f"=======================================================")
        return df
