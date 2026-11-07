"""Optional Streamlit wizard for SciMapper.

Install with: pip install 'scimapper[web]'
Run with: streamlit run streamlit_app.py  (or: python main.py --web)
"""

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover
    raise SystemExit("Streamlit is not installed. Install with: pip install 'scimapper[web]'") from exc

import io
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils import validate_config
from main import cmd_run_discovery, cmd_compile, cmd_build_doc

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "config_template.json")

DOMAIN_PRESETS = {
    "software_engineering": "sentence-transformers/all-MiniLM-L6-v2",
    "biomedical_health": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract",
    "scientific_general": "allenai/scibert_scivocab_uncased",
    "finance_business": "ProsusAI/finbert",
    "multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
}

I18N = {
    "English": {
        "title": "SciMapper - Configuration Wizard",
        "upload": "Optional: load an existing config JSON",
        "step": "Step {step}/6",
        "meta": "1) Project metadata",
        "title_field": "Study title",
        "short_name": "Short name (no spaces)",
        "authors": "Authors (comma separated)",
        "year_start": "Start year",
        "year_end": "End year",
        "output_dir": "Output folder",
        "output_help": "Created automatically from the short name. You can change it.",
        "rqs": "2) Research questions (RQs)",
        "search": "3) Search strategy (OpenAlex)",
        "email": "Courtesy email (OpenAlex)",
        "max_results": "Max results per query",
        "queries": "Queries (one per line)",
        "nlp": "4) NLP tuning",
        "preset": "Domain preset",
        "clusters": "Number of clusters",
        "stopwords": "Stop words",
        "synth": "5) Qualitative synthesis",
        "candidates": "Candidates per topic",
        "min_cites": "Minimum citation threshold",
        "review": "6) Review and run",
        "valid": "Configuration is valid ✅",
        "invalid": "Fix these errors before running:",
        "run_discovery": "1) Run discovery",
        "compile": "2) Compile",
        "build_doc": "3) Build doc",
        "download": "Download config JSON",
        "prev": "⬅ Back",
        "next": "Next ➡",
        "reset": "Restart wizard",
        "language": "Language",
    },
    "Español": {
        "title": "SciMapper - Asistente de Configuración",
        "upload": "Opcional: cargar config JSON existente",
        "step": "Paso {step}/6",
        "meta": "1) Metadatos del proyecto",
        "title_field": "Título del estudio",
        "short_name": "Nombre corto (sin espacios)",
        "authors": "Autores (separados por coma)",
        "year_start": "Año inicial",
        "year_end": "Año final",
        "output_dir": "Carpeta de salida",
        "output_help": "Se crea automáticamente a partir del nombre corto. Puedes cambiarla.",
        "rqs": "2) Preguntas de investigación (RQs)",
        "search": "3) Estrategia de búsqueda (OpenAlex)",
        "email": "Email de cortesía (OpenAlex)",
        "max_results": "Resultados máximos por consulta",
        "queries": "Consultas (una por línea)",
        "nlp": "4) Ajuste NLP",
        "preset": "Preset de dominio",
        "clusters": "Número de clusters",
        "stopwords": "Stop words",
        "synth": "5) Síntesis cualitativa",
        "candidates": "Candidatos por tópico",
        "min_cites": "Umbral mínimo de citas",
        "review": "6) Revisión y ejecución",
        "valid": "Configuración válida ✅",
        "invalid": "Corrige estos errores antes de ejecutar:",
        "run_discovery": "1) Ejecutar discovery",
        "compile": "2) Compilar",
        "build_doc": "3) Generar documento",
        "download": "Descargar config JSON",
        "prev": "⬅ Anterior",
        "next": "Siguiente ➡",
        "reset": "Reiniciar asistente",
        "language": "Idioma",
    },
}


def t(key, **kwargs):
    lang = st.session_state.get("language", "English")
    text = I18N[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text


def load_template() -> dict:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def init_state():
    if "step" not in st.session_state:
        st.session_state["step"] = 0
    if "language" not in st.session_state:
        st.session_state["language"] = "English"
    if "cfg" not in st.session_state:
        st.session_state["cfg"] = load_template()
    if "queries_text" not in st.session_state:
        st.session_state["queries_text"] = "\n".join(st.session_state["cfg"].get("search_strategy", {}).get("queries", []))


def main():
    st.set_page_config(page_title="SciMapper Wizard", layout="wide")
    init_state()

    lang = st.selectbox(t("language"), ["English", "Español"], index=0 if st.session_state["language"] == "English" else 1)
    st.session_state["language"] = lang

    st.title(t("title"))

    uploaded = st.file_uploader(t("upload"), type=["json"])
    if uploaded is not None:
        try:
            st.session_state["cfg"] = json.loads(uploaded.getvalue().decode("utf-8"))
            st.session_state["queries_text"] = "\n".join(st.session_state["cfg"].get("search_strategy", {}).get("queries", []))
            st.success("Config loaded." if lang == "English" else "Configuración cargada.")
        except Exception as e:
            st.error(f"Invalid JSON: {e}" if lang == "English" else f"JSON inválido: {e}")

    step = st.session_state["step"]
    cfg = st.session_state["cfg"]
    meta = cfg.setdefault("project_metadata", {})
    rqs = cfg.setdefault("research_questions", {})
    strat = cfg.setdefault("search_strategy", {})
    nlp = cfg.setdefault("nlp_tuning", {})
    synth = cfg.setdefault("qualitative_synthesis", {})

    st.progress((step + 1) / 6, text=t("step", step=step + 1))

    if step == 0:
        st.subheader(t("meta"))
        meta["title"] = st.text_input(t("title_field"), meta.get("title", ""), help="Formal title of the study.")
        meta["short_name"] = st.text_input(t("short_name"), meta.get("short_name", "SMS_Proyecto"), help="Used to name the output folder.")
        authors_str = st.text_input(t("authors"), ", ".join(meta.get("authors", [])))
        meta["authors"] = [a.strip() for a in authors_str.split(",") if a.strip()]
        years = meta.get("temporal_window", [2018, 2026])
        y0 = st.number_input(t("year_start"), value=int(years[0]), min_value=1900, max_value=2100)
        y1 = st.number_input(t("year_end"), value=int(years[1]), min_value=1900, max_value=2100)
        meta["temporal_window"] = [int(y0), int(y1)]

        default_out = f"./output_{meta['short_name']}" if meta.get("short_name") else "./output"
        if meta.get("output_dir", "./output") in ("./output", ""):
            meta["output_dir"] = default_out
        meta["output_dir"] = st.text_input(t("output_dir"), meta.get("output_dir", default_out), help=t("output_help"))

    elif step == 1:
        st.subheader(t("rqs"))
        for key in ["RQ1", "RQ2", "RQ3"]:
            rqs[key] = st.text_area(key, rqs.get(key, ""), height=80)

    elif step == 2:
        st.subheader(t("search"))
        strat["openalex_email"] = st.text_input(t("email"), strat.get("openalex_email", ""), help="Used for the OpenAlex polite pool.")
        strat["max_results_per_query"] = st.slider(t("max_results"), 10, 300, int(strat.get("max_results_per_query", 100)))
        st.session_state["queries_text"] = st.text_area(t("queries"), st.session_state["queries_text"], height=180)
        strat["queries"] = [q.strip() for q in st.session_state["queries_text"].splitlines() if q.strip()]

    elif step == 3:
        st.subheader(t("nlp"))
        preset_keys = list(DOMAIN_PRESETS.keys())
        current = nlp.get("domain_preset", "software_engineering")
        idx = preset_keys.index(current) if current in preset_keys else 0
        preset = st.selectbox(t("preset"), preset_keys, index=idx)
        nlp["domain_preset"] = preset
        nlp["domain_presets_catalog"] = DOMAIN_PRESETS
        nlp["embedding_model"] = DOMAIN_PRESETS[preset]
        nlp["n_clusters"] = st.slider(t("clusters"), 2, 12, int(nlp.get("n_clusters", 6)))
        sw = nlp.get("stop_words", "english")
        nlp["stop_words"] = st.selectbox(t("stopwords"), ["english", "none"], index=0 if sw == "english" else 1)

    elif step == 4:
        st.subheader(t("synth"))
        synth["candidates_per_topic"] = st.slider(t("candidates"), 1, 10, int(synth.get("candidates_per_topic", 3)))
        synth["min_citations"] = st.number_input(t("min_cites"), value=int(synth.get("min_citations", 1)), min_value=0, max_value=1000)

    elif step == 5:
        st.subheader(t("review"))
        errors = validate_config(cfg)
        if errors:
            st.error(t("invalid"))
            for e in errors:
                st.write(f"- {e}")
        else:
            st.success(t("valid"))

        st.json(cfg)

        disabled = bool(errors)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(t("run_discovery"), disabled=disabled, type="primary"):
                with st.spinner("Running discovery..." if st.session_state["language"] == "English" else "Ejecutando discovery..."):
                    cmd_run_discovery(cfg, "sms_config.json")
                st.success("Discovery finished." if st.session_state["language"] == "English" else "Discovery finalizado.")
        with col2:
            if st.button(t("compile"), disabled=disabled, type="primary"):
                with st.spinner("Compiling..." if st.session_state["language"] == "English" else "Compilando..."):
                    cmd_compile(cfg)
                st.success("Compilation finished." if st.session_state["language"] == "English" else "Compilación finalizada.")
        with col3:
            if st.button(t("build_doc"), disabled=disabled, type="primary"):
                with st.spinner("Building document..." if st.session_state["language"] == "English" else "Generando documento..."):
                    cmd_build_doc(cfg)
                st.success("Document generated." if st.session_state["language"] == "English" else "Documento generado.")

        out_dir = os.path.abspath(cfg.get("project_metadata", {}).get("output_dir", "./output"))
        st.subheader("Resultados generados" if st.session_state["language"] == "Español" else "Generated results")
        if os.path.exists(out_dir):
            files = sorted(os.listdir(out_dir))
            st.write(files)
            if st.button("Crear ZIP de resultados" if st.session_state["language"] == "Español" else "Create results ZIP"):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    for root, _, fs in os.walk(out_dir):
                        for f in fs:
                            full = os.path.join(root, f)
                            arc = os.path.relpath(full, out_dir)
                            z.write(full, arc)
                buf.seek(0)
                short = cfg.get("project_metadata", {}).get("short_name", "SciMapper")
                st.download_button(
                    "Descargar ZIP" if st.session_state["language"] == "Español" else "Download ZIP",
                    data=buf.getvalue(),
                    file_name=f"{short}_resultados.zip",
                    mime="application/zip",
                )
        else:
            st.info("Aún no hay carpeta de salida. Ejecuta el pipeline primero." if st.session_state["language"] == "Español" else "No output folder yet. Run the pipeline first.")

        st.download_button(
            t("download"),
            data=json.dumps(cfg, indent=2, ensure_ascii=False),
            file_name="sms_config.json",
            mime="application/json",
        )

    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if step > 0 and st.button(t("prev")):
            st.session_state["step"] -= 1
            st.rerun()
    with col_next:
        if step < 5 and st.button(t("next")):
            st.session_state["step"] += 1
            st.rerun()

    if step == 5 and st.button(t("reset")):
        st.session_state["step"] = 0
        st.session_state["cfg"] = load_template()
        st.session_state["queries_text"] = "\n".join(st.session_state["cfg"].get("search_strategy", {}).get("queries", []))
        st.rerun()


if __name__ == "__main__":
    main()