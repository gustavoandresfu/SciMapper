"""Optional Streamlit wizard for SciMapper.

Install with: pip install 'scimapper[web]'
Run with: streamlit run streamlit_app.py  (or: python main.py --web)
"""

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover
    raise SystemExit("Streamlit is not installed. Install with: pip install 'scimapper[web]'") from exc

import json
import os
import sys

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


def load_template() -> dict:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def init_state():
    if "step" not in st.session_state:
        st.session_state["step"] = 0
    if "cfg" not in st.session_state:
        st.session_state["cfg"] = load_template()
    if "queries_text" not in st.session_state:
        st.session_state["queries_text"] = "\n".join(st.session_state["cfg"].get("search_strategy", {}).get("queries", []))


def build_config_from_state():
    cfg = st.session_state["cfg"]
    return cfg


def main():
    st.set_page_config(page_title="SciMapper Wizard", layout="wide")
    st.title("SciMapper - Asistente de Configuración (Wizard)")
    init_state()

    uploaded = st.file_uploader("Opcional: cargar config JSON existente", type=["json"])
    if uploaded is not None:
        try:
            st.session_state["cfg"] = json.loads(uploaded.getvalue().decode("utf-8"))
            st.session_state["queries_text"] = "\n".join(st.session_state["cfg"].get("search_strategy", {}).get("queries", []))
            st.success("Configuración cargada.")
        except Exception as e:
            st.error(f"JSON inválido: {e}")

    step = st.session_state["step"]
    cfg = st.session_state["cfg"]
    meta = cfg.setdefault("project_metadata", {})
    rqs = cfg.setdefault("research_questions", {})
    strat = cfg.setdefault("search_strategy", {})
    nlp = cfg.setdefault("nlp_tuning", {})
    synth = cfg.setdefault("qualitative_synthesis", {})

    st.progress((step + 1) / 6, text=f"Paso {step + 1} de 6")

    if step == 0:
        st.subheader("1) Metadatos del proyecto")
        meta["title"] = st.text_input("Título del estudio", meta.get("title", ""))
        meta["short_name"] = st.text_input("Nombre corto (sin espacios)", meta.get("short_name", "SMS_Proyecto"))
        authors_str = st.text_input("Autores (separados por coma)", ", ".join(meta.get("authors", [])))
        meta["authors"] = [a.strip() for a in authors_str.split(",") if a.strip()]
        years = meta.get("temporal_window", [2018, 2026])
        y0 = st.number_input("Año inicial", value=int(years[0]), min_value=1900, max_value=2100)
        y1 = st.number_input("Año final", value=int(years[1]), min_value=1900, max_value=2100)
        meta["temporal_window"] = [int(y0), int(y1)]
        meta["output_dir"] = st.text_input("Carpeta de salida", meta.get("output_dir", "./output"))

    elif step == 1:
        st.subheader("2) Preguntas de investigación (RQs)")
        for key in ["RQ1", "RQ2", "RQ3"]:
            rqs[key] = st.text_area(key, rqs.get(key, ""), height=80)

    elif step == 2:
        st.subheader("3) Estrategia de búsqueda (OpenAlex)")
        strat["openalex_email"] = st.text_input("Email de cortesía (OpenAlex)", strat.get("openalex_email", ""))
        strat["max_results_per_query"] = st.slider("Resultados máximos por consulta", 10, 300, int(strat.get("max_results_per_query", 100)))
        st.session_state["queries_text"] = st.text_area(
            "Consultas (una por línea)", st.session_state["queries_text"], height=180
        )
        strat["queries"] = [q.strip() for q in st.session_state["queries_text"].splitlines() if q.strip()]

    elif step == 3:
        st.subheader("4) Ajuste NLP")
        preset = st.selectbox("Preset de dominio", list(DOMAIN_PRESETS.keys()), index=list(DOMAIN_PRESETS.keys()).index(nlp.get("domain_preset", "software_engineering")) if nlp.get("domain_preset", "software_engineering") in DOMAIN_PRESETS else 0)
        nlp["domain_preset"] = preset
        nlp["domain_presets_catalog"] = DOMAIN_PRESETS
        nlp["embedding_model"] = DOMAIN_PRESETS[preset]
        nlp["n_clusters"] = st.slider("Número de clusters", 2, 12, int(nlp.get("n_clusters", 6)))
        nlp["stop_words"] = st.selectbox("Stop words", ["english", "none"], index=0 if nlp.get("stop_words", "english") == "english" else 1)

    elif step == 4:
        st.subheader("5) Síntesis cualitativa")
        synth["candidates_per_topic"] = st.slider("Candidatos por tópico", 1, 10, int(synth.get("candidates_per_topic", 3)))
        synth["min_citations"] = st.number_input("Umbral mínimo de citas", value=int(synth.get("min_citations", 1)), min_value=0, max_value=1000)

    elif step == 5:
        st.subheader("6) Revisión y ejecución")
        errors = validate_config(cfg)
        if errors:
            st.error("Corrige estos errores antes de ejecutar:")
            for e in errors:
                st.write(f"- {e}")
        else:
            st.success("Configuración válida ✅")

        st.json(cfg)

        disabled = bool(errors)
        col1, col2, col3 = st.columns(3)
        if col1.button("Run discovery", disabled=disabled):
            with st.spinner("Ejecutando discovery..."):
                cmd_run_discovery(cfg, "sms_config.json")
            st.success("Discovery finalizado.")
        if col2.button("Compile", disabled=disabled):
            with st.spinner("Compilando..."):
                cmd_compile(cfg)
            st.success("Compilación finalizada.")
        if col3.button("Build doc", disabled=disabled):
            with st.spinner("Generando documento..."):
                cmd_build_doc(cfg)
            st.success("Documento generado.")

        st.download_button(
            "Descargar config JSON",
            data=json.dumps(cfg, indent=2, ensure_ascii=False),
            file_name="sms_config.json",
            mime="application/json",
        )

    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if step > 0 and st.button("⬅ Anterior"):
            st.session_state["step"] -= 1
            st.rerun()
    with col_next:
        if step < 5 and st.button("Siguiente ➡"):
            st.session_state["step"] += 1
            st.rerun()

    if step == 5:
        if st.button("Reiniciar wizard"):
            st.session_state["step"] = 0
            st.session_state["cfg"] = load_template()
            st.session_state["queries_text"] = "\n".join(st.session_state["cfg"].get("search_strategy", {}).get("queries", []))
            st.rerun()


if __name__ == "__main__":
    main()