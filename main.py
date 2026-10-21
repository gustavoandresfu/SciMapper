#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SciMapper - Unified CLI Orchestrator
====================================
Automated Scientific Mapping & Systematic Literature Reviews with Dense Semantic Clustering.

Main commands:
  scimapper --init
  scimapper --run-discovery --config sms_config.json
  scimapper --compile --config sms_config.json
  scimapper --build-doc --config sms_config.json
  scimapper --all --config sms_config.json
"""

import os
import sys
import json
import shutil
import argparse
import pandas as pd
import numpy as np

# Soporte para salida unicode en consolas Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Importar módulos del core
from core.collector import AutoCollector
from core.embedder import AutoEmbedder
from core.clusterer import AutoClusterer
from core.visualizer import AutoVisualizer
from core.selector import AutoSelector
from core.doc_builder import AutoDocBuilder

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        print(f"❌ Error: El archivo de configuración '{config_path}' no existe.")
        print("💡 Ejecuta 'python main.py --init' para generar una plantilla base.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def cmd_init(target_path: str = "sms_config.json"):
    template_path = os.path.join(os.path.dirname(__file__), "config_template.json")
    if os.path.exists(target_path):
        print(f"⚠️ El archivo '{target_path}' ya existe. No se sobrescribirá.")
        return
    shutil.copy(template_path, target_path)
    print(f"✅ Plantilla de configuración creada con éxito en: {target_path}")
    print("📝 Ábrelo y personaliza tus preguntas de investigación (RQs), consultas OpenAlex y preset de dominio.")

def cmd_run_discovery(config: dict, config_path: str):
    print("=" * 70)
    print(f"🚀 FASE 1: DESCUBRIMIENTO AUTOMATIZADO (DISCOVERY PIPELINE)")
    print(f"   Proyecto: {config.get('project_metadata', {}).get('title', 'SMS')}")
    print("=" * 70)

    output_dir = config.get("project_metadata", {}).get("output_dir", "./output")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Recolección
    collector = AutoCollector(config)
    df = collector.run()
    if df.empty:
        print("❌ No se encontraron artículos con los criterios especificados.")
        sys.exit(1)

    # 2. Embeddings
    embedder = AutoEmbedder(config)
    embeddings = embedder.encode(df)

    # 3. Clustering y c-TF-IDF
    clusterer = AutoClusterer(config)
    df_clustered, topics_summary = clusterer.run(df, embeddings)

    # Guardar dataframe intermedio con coordenadas
    inter_path = os.path.join(output_dir, "corpus_intermedio_con_coords.csv")
    df_clustered.to_csv(inter_path, index=False, encoding="utf-8-sig")

    # 4. Recomendación Estratificada de Artículos para la Discusión (Selector)
    selector = AutoSelector(config)
    selector.select_candidates(df_clustered, embeddings, topics_summary)

    print("\n" + "=" * 70)
    print("🎯 FASE 1 COMPLETADA CON ÉXITO")
    print("=" * 70)
    print(f"📂 Archivo de Tópicos Descubiertos:    {os.path.join(output_dir, 'discovered_topics.json')}")
    print(f"📂 Archivo de Candidatos a Discusión: {os.path.join(output_dir, 'candidatos_discusion.json')}")
    print("\n👉 PASOS HUMANOS REQUERIDOS (Human-in-the-Loop):")
    print("   1. Ajuste Temático: Abre 'discovered_topics.json' y asigna nombres académicos en 'assigned_name'.")
    print("      (Si algún tópico no corresponde al estudio, marca 'exclude_prisma': true).")
    print("   2. Selección para Discusión: Abre 'candidatos_discusion.json' y revisa los artículos sugeridos.")
    print("      (Marca 'selected_for_deep_review': true en los 8-10 que leerás a texto completo).")
    print(f"   3. Una vez ajustados, compila y genera el documento Word:")
    print(f"      python main.py --compile --config {config_path}")
    print(f"      python main.py --build-doc --config {config_path}")
    print("=" * 70)

def cmd_recommend_papers(config: dict):
    output_dir = config.get("project_metadata", {}).get("output_dir", "./output")
    inter_csv_path = os.path.join(output_dir, "corpus_intermedio_con_coords.csv")
    topics_json_path = os.path.join(output_dir, "discovered_topics.json")
    cache_file = os.path.join(output_dir, "embeddings_cache.npy")

    if not os.path.exists(inter_csv_path) or not os.path.exists(cache_file) or not os.path.exists(topics_json_path):
        print("❌ Faltan archivos intermedios. Ejecuta primero '--run-discovery'.")
        return

    df = pd.read_csv(inter_csv_path)
    embeddings = np.load(cache_file)
    with open(topics_json_path, "r", encoding="utf-8") as f:
        topics_info = json.load(f)

    selector = AutoSelector(config)
    selector.select_candidates(df, embeddings, topics_info)

def cmd_compile(config: dict):
    print("=" * 70)
    print(f"📊 FASE 2: COMPILACIÓN Y CONSOLIDACIÓN ACADÉMICA")
    print(f"   Proyecto: {config.get('project_metadata', {}).get('title', 'SMS')}")
    print("=" * 70)

    output_dir = config.get("project_metadata", {}).get("output_dir", "./output")
    topics_json_path = os.path.join(output_dir, "discovered_topics.json")
    inter_csv_path = os.path.join(output_dir, "corpus_intermedio_con_coords.csv")

    if not os.path.exists(topics_json_path) or not os.path.exists(inter_csv_path):
        print("❌ Faltan archivos intermedios de la Fase 1.")
        print("💡 Primero debes ejecutar: python main.py --run-discovery")
        sys.exit(1)

    with open(topics_json_path, "r", encoding="utf-8") as f:
        topics_info = json.load(f)

    df = pd.read_csv(inter_csv_path)
    initial_count = len(df)

    # Auditar exclusiones humanas según PRISMA
    excluded_topics = [int(k) for k, v in topics_info.items() if v.get("exclude_prisma", False)]
    if excluded_topics:
        print(f"🛑 Filtrando tópicos marcados para exclusión PRISMA: {excluded_topics}")
        excluded_df = df[df["topic_id"].isin(excluded_topics)]
        df = df[~df["topic_id"].isin(excluded_topics)]
        print(f"   Registros excluidos por criterio humano: {len(excluded_df)}")
        print(f"   Registros finales retenidos:             {len(df)}")
    else:
        print("ℹ️ No se marcaron tópicos para exclusión; se retiene el 100% del corpus agrupado.")

    # Visualización y exportación final
    visualizer = AutoVisualizer(config)
    map_path = visualizer.build_interactive_map(df, topics_info)
    dataset_path = visualizer.save_final_dataset(df)

    # Generar reporte PRISMA resumido
    report_path = os.path.join(output_dir, "prisma_summary_report.txt")
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(f"REPORTE DE AUDITORÍA PRISMA 2020 - {config.get('project_metadata', {}).get('title')}\n")
        rf.write("=" * 70 + "\n\n")
        rf.write(f"1. Identificación Inicial (Corpus Bruto):  {initial_count} registros\n")
        rf.write(f"2. Exclusiones por Criterio Temático Humano: {initial_count - len(df)} registros\n")
        rf.write(f"3. Corpus Final Incluido para Mapeo:        {len(df)} registros\n\n")
        rf.write("DISTRIBUCIÓN POR TÓPICOS:\n")
        for tid, info in topics_info.items():
            status = "[EXCLUIDO]" if info.get("exclude_prisma", False) else "[INCLUIDO]"
            rf.write(f"  - {status} {info.get('assigned_name')}: {info.get('count')} arts ({info.get('percentage')}%)\n")
            rf.write(f"    Palabras clave: {', '.join(info.get('keywords', []))}\n")

    print(f"✔ Reporte de auditoría PRISMA generado en: {report_path}")
    print("\n" + "=" * 70)
    print("🎉 MAPEO SISTEMÁTICO COMPLETADO Y CONSOLIDADO")
    print(f"   1. Dataset final:    {dataset_path}")
    print(f"   2. Mapa interactivo: {map_path}")
    print(f"   3. Reporte PRISMA:   {report_path}")
    print("=" * 70)

def cmd_build_doc(config: dict):
    print("=" * 70)
    print(f"📝 FASE 3: GENERACIÓN DEL BORRADOR EN MICROSOFT WORD (.docx)")
    print(f"   Proyecto: {config.get('project_metadata', {}).get('title', 'SMS')}")
    print("=" * 70)

    doc_builder = AutoDocBuilder(config)
    out_docx = doc_builder.generate_draft()
    print("=" * 70)
    print(f"🎉 Borrador generado exitosamente en: {out_docx}")
    print("   Contiene: Portada, RQs, Tabla PRISMA 2020, Tabla de Taxonomías,")
    print("   Matriz de Discusión con papers seleccionados y secciones preparadas.")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(
        description="SciMapper: Automated Scientific Mapping & Systematic Literature Reviews with Dense Semantic Clustering.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--init", action="store_true", help="Genera una plantilla 'sms_config.json' para un nuevo proyecto.")
    parser.add_argument("--config", type=str, default="sms_config.json", help="Ruta al archivo de configuración JSON.")
    parser.add_argument("--run-discovery", action="store_true", help="Fase 1: Recolecta artículos, genera embeddings, clusters, discovered_topics.json y candidatos a discusión.")
    parser.add_argument("--recommend-papers", action="store_true", help="Reejecuta el recomendador estratificado de artículos para la discusión.")
    parser.add_argument("--compile", action="store_true", help="Fase 2: Aplica ajustes humanos y genera mapas interactivos y reportes finales.")
    parser.add_argument("--build-doc", action="store_true", help="Fase 3: Construye el borrador formal de paper en Microsoft Word (.docx).")
    parser.add_argument("--all", action="store_true", help="Ejecuta todo el pipeline de punta a punta (Discovery + Compile + Build Doc).")

    args = parser.parse_args()

    if args.init:
        cmd_init(args.config)
        return

    if args.run_discovery:
        cfg = load_config(args.config)
        cmd_run_discovery(cfg, args.config)
        return

    if args.recommend_papers:
        cfg = load_config(args.config)
        cmd_recommend_papers(cfg)
        return

    if args.compile:
        cfg = load_config(args.config)
        cmd_compile(cfg)
        return

    if args.build_doc:
        cfg = load_config(args.config)
        cmd_build_doc(cfg)
        return

    if args.all:
        cfg = load_config(args.config)
        cmd_run_discovery(cfg, args.config)
        cmd_compile(cfg)
        cmd_build_doc(cfg)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
