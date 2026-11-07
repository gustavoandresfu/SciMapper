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
import logging
import pandas as pd
import numpy as np

__version__ = "1.0.1"

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
from core.utils import validate_config, setup_logging, write_manifest

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        print(f"❌ Error: El archivo de configuración '{config_path}' no existe.")
        print("💡 Ejecuta 'python main.py --init' para generar una plantilla base.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    errors = validate_config(cfg)
    if errors:
        print("❌ Configuración inválida:")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)
    return cfg

def cmd_init(target_path: str = "sms_config.json", quick: bool = False):
    template_path = os.path.join(os.path.dirname(__file__), "config_template.json")
    if os.path.exists(target_path):
        print(f"⚠️ El archivo '{target_path}' ya existe.")
        try:
            if sys.stdin.isatty() and not quick:
                resp = input("   ¿Deseas sobrescribirlo con una nueva configuración? (s/N): ").strip().lower()
                if resp not in ["s", "si", "y", "yes"]:
                    print("Operación cancelada. El archivo original no fue modificado.")
                    return
            else:
                print("   No se sobrescribirá. Usa otro nombre con --config si deseas crear uno nuevo.")
                return
        except Exception:
            return

    with open(template_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Si se pide quick o no hay terminal interactiva (TTY), copiar plantilla estándar
    if quick or not sys.stdin.isatty():
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"✅ Plantilla estándar creada con éxito en: {target_path}")
        print("📝 Ábrelo y personaliza tus preguntas de investigación (RQs), consultas OpenAlex y preset de dominio.")
        return

    # Asistente interactivo
    print("=" * 70)
    print("🚀 SciMapper - Asistente Interactivo de Inicialización")
    print("======================================================================")
    print("Configura los datos clave de tu proyecto en pocos pasos.")
    print("(Presiona [Enter] en cualquier opción para aceptar el valor por defecto)\n")

    def prompt(text: str, default: str) -> str:
        try:
            val = input(f"{text} [{default}]: ").strip()
            return val if val else default
        except (EOFError, KeyboardInterrupt):
            print("\nOperación cancelada.")
            sys.exit(0)

    # 1. Metadatos
    title = prompt("1. Título formal del estudio", cfg.get("project_metadata", {}).get("title", "Mapeo Sistemático"))
    short_name = prompt("2. Identificador corto del proyecto", "SMS_Estudio")
    author = prompt("3. Autor(es) principal(es)", "Investigador Principal")
    email = prompt("4. Correo de contacto (cortesía OpenAlex API)", "investigador@universidad.edu")

    # 2. Catálogo de disciplinas
    presets = [
        ("software_engineering", "💻 Computación, Software e Inteligencia Artificial", "all-MiniLM-L6-v2"),
        ("biomedical_health", "🩺 Medicina, Salud, Biología y Farmacia", "PubMedBERT"),
        ("scientific_general", "🔬 Ciencias Exactas y Naturales (Física/Química)", "SciBERT"),
        ("finance_business", "📈 Economía, Finanzas y Negocios", "FinBERT"),
        ("multilingual", "🌐 Multilingüe / Literatura en Español", "Multilingual-MiniLM")
    ]

    print("\n5. Selecciona la disciplina de tu investigación:")
    for idx, (code, label, model_short) in enumerate(presets, 1):
        print(f"   [{idx}] {label} ({model_short})")

    sel_idx = 1
    while True:
        choice = prompt("   Elige una opción (1-5)", "1")
        if choice.isdigit() and 1 <= int(choice) <= len(presets):
            sel_idx = int(choice)
            break
        print("   ⚠️ Por favor, ingresa un número válido entre 1 y 5.")

    chosen_preset, chosen_label, chosen_model = presets[sel_idx - 1]

    # 3. Cantidad de clusters
    n_clusters = 6
    while True:
        c_val = prompt("\n6. Cantidad sugerida de familias/clusters a descubrir (3-10)", "6")
        if c_val.isdigit() and 3 <= int(c_val) <= 12:
            n_clusters = int(c_val)
            break
        print("   ⚠️ Ingresa un número entre 3 y 10.")

    # 4. Estrategia de búsqueda iterativa con guía de buenas prácticas
    print("\n7. Estrategia de Búsqueda Académica (OpenAlex):")
    print("   💡 Buenas prácticas metodológicas:")
    print("      • Usa comillas dobles para frases exactas: \"deep learning\"")
    print("      • Cruza conceptos con AND: \"machine learning\" AND \"cardiology\"")
    print("      • Usa OR entre paréntesis para sinónimos: (\"llm\" OR \"generative ai\") AND \"testing\"")
    print("   (Puedes ingresar 1 o varias consultas. Presiona [Enter] sin texto para finalizar)\n")

    user_queries = []
    q_num = 1
    while True:
        prompt_label = f"   • Consulta de búsqueda #{q_num}" + (" (Enter para usar ejemplos)" if q_num == 1 else " (opcional, Enter para finalizar)")
        q_val = prompt(prompt_label, "").strip()

        if not q_val:
            if q_num == 1:
                print("   ℹ️ Se mantendrán las consultas de ejemplo predeterminadas.")
            break

        # Ayuda preventiva: si el usuario no usó comillas y tiene espacios, advertir amigablemente
        if '"' not in q_val and " " in q_val and " AND " not in q_val:
            print("     💡 Tip: No incluiste comillas ni AND. Se recomienda buscar frases exactas como: \"...\".")

        user_queries.append(q_val)
        print(f"     ✔ Consulta #{q_num} agregada con éxito.")
        q_num += 1

    # Actualizar la configuración
    cfg["project_metadata"]["title"] = title
    cfg["project_metadata"]["short_name"] = short_name
    cfg["project_metadata"]["authors"] = [a.strip() for a in author.split(",")]
    cfg["search_strategy"]["openalex_email"] = email
    cfg["nlp_tuning"]["domain_preset"] = chosen_preset
    cfg["nlp_tuning"]["n_clusters"] = n_clusters

    if user_queries:
        cfg["search_strategy"]["queries"] = user_queries

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"🎉 ¡Proyecto configurado exitosamente en: '{target_path}'!")
    print(f"   • Disciplina: {chosen_label}")
    print(f"   • Modelo IA:  {chosen_model}")
    print(f"   • Clusters:   {n_clusters}")
    print("=" * 70)
    print("👉 Próximos pasos:")
    print(f"   1. Abre '{target_path}' si deseas ajustar tus preguntas (RQs) o añadir más queries.")
    print(f"   2. Ejecuta la búsqueda y agrupamiento con:")
    print(f"      python main.py --run-discovery --config {target_path}")
    print("=" * 70)

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

    write_manifest(output_dir, config, {"corpus_final": len(df_clustered), "topics": len(topics_summary)})

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
    parser.add_argument("--init", action="store_true", help="Genera una plantilla 'sms_config.json' para un nuevo proyecto (asistente guiado).")
    parser.add_argument("--quick", action="store_true", help="Genera la plantilla directamente sin abrir el asistente interactivo.")
    parser.add_argument("--config", type=str, default="sms_config.json", help="Ruta al archivo de configuración JSON.")
    parser.add_argument("--run-discovery", action="store_true", help="Fase 1: Recolecta artículos, genera embeddings, clusters, discovered_topics.json y candidatos a discusión.")
    parser.add_argument("--recommend-papers", action="store_true", help="Reejecuta el recomendador estratificado de artículos para la discusión.")
    parser.add_argument("--compile", action="store_true", help="Fase 2: Aplica ajustes humanos y genera mapas interactivos y reportes finales.")
    parser.add_argument("--build-doc", action="store_true", help="Fase 3: Construye el borrador formal de paper en Microsoft Word (.docx).")
    parser.add_argument("--all", action="store_true", help="Ejecuta todo el pipeline de punta a punta (Discovery + Compile + Build Doc).")
    parser.add_argument("--version", action="version", version=f"SciMapper {__version__}")
    parser.add_argument("--verbose", action="store_true", help="Activa salida detallada (logging DEBUG).")

    args = parser.parse_args()
    setup_logging(verbose=getattr(args, "verbose", False))

    if args.init:
        cmd_init(args.config, quick=args.quick)
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
