"""Utility helpers for SciMapper: logging, validation and reproducibility."""

import json
import logging
import os
import hashlib
from datetime import datetime


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("scimapper")


def validate_config(config: dict) -> list:
    """Return a list of validation errors (empty if valid)."""
    errors = []
    meta = config.get("project_metadata", {})
    if not isinstance(meta, dict):
        errors.append("project_metadata debe ser un objeto.")
        return errors

    if not meta.get("title"):
        errors.append("project_metadata.title es obligatorio.")
    if not meta.get("short_name"):
        errors.append("project_metadata.short_name es obligatorio.")

    years = meta.get("temporal_window", [])
    if not (isinstance(years, list) and len(years) == 2):
        errors.append("project_metadata.temporal_window debe ser [año_inicio, año_fin].")
    else:
        try:
            y0, y1 = int(years[0]), int(years[1])
            if y0 > y1:
                errors.append("temporal_window: el año inicial no puede ser mayor al final.")
            if y0 < 1900 or y1 > 2100:
                errors.append("temporal_window: rango de años fuera de límites razonables.")
        except (TypeError, ValueError):
            errors.append("temporal_window debe contener enteros.")

    strategy = config.get("search_strategy", {})
    queries = strategy.get("queries", [])
    if not isinstance(queries, list) or not queries:
        errors.append("search_strategy.queries debe ser una lista no vacía.")
    if not strategy.get("openalex_email"):
        errors.append("search_strategy.openalex_email es obligatorio.")

    nlp = config.get("nlp_tuning", {})
    k = nlp.get("n_clusters", 6)
    try:
        if int(k) < 2 or int(k) > 50:
            errors.append("nlp_tuning.n_clusters debe estar entre 2 y 50.")
    except (TypeError, ValueError):
        errors.append("nlp_tuning.n_clusters debe ser entero.")

    return errors


def config_hash(config: dict) -> str:
    blob = json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def write_manifest(output_dir: str, config: dict, counts: dict) -> str:
    os.makedirs(output_dir, exist_ok=True)
    manifest = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "config_hash": config_hash(config),
        "counts": counts,
    }
    path = os.path.join(output_dir, "run_manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return path
