"""Optional Streamlit demo for SciMapper.

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


def load_template() -> dict:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    st.set_page_config(page_title="SciMapper", layout="wide")
    st.title("SciMapper - Systematic Mapping Demo")

    if "config_text" not in st.session_state:
        try:
            st.session_state["config_text"] = json.dumps(load_template(), indent=2, ensure_ascii=False)
        except Exception:
            st.session_state["config_text"] = "{}"

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Configuración (JSON)")
        uploaded = st.file_uploader("Subir config JSON", type=["json"])
        if uploaded is not None:
            st.session_state["config_text"] = uploaded.getvalue().decode("utf-8")

        config_text = st.text_area("Edita el JSON de configuración", st.session_state["config_text"], height=420)
        st.session_state["config_text"] = config_text

    cfg = None
    errors = []
    try:
        cfg = json.loads(config_text)
        errors = validate_config(cfg)
    except json.JSONDecodeError as e:
        errors = [f"JSON inválido: {e}"]

    with right:
        st.subheader("Estado")
        if errors:
            st.error("Configuración inválida:")
            for e in errors:
                st.write(f"- {e}")
        else:
            st.success("Configuración válida ✅")
            st.json(cfg)

        st.subheader("Ejecutar pipeline")
        disabled = bool(errors) or cfg is None
        if st.button("1) Run discovery", disabled=disabled):
            with st.spinner("Ejecutando discovery..."):
                cmd_run_discovery(cfg, "sms_config.json")
            st.success("Discovery finalizado.")
        if st.button("2) Compile", disabled=disabled):
            with st.spinner("Compilando..."):
                cmd_compile(cfg)
            st.success("Compilación finalizada.")
        if st.button("3) Build doc", disabled=disabled):
            with st.spinner("Generando documento..."):
                cmd_build_doc(cfg)
            st.success("Documento generado.")

        st.info("Los archivos se guardan en el output_dir definido en la configuración.")


if __name__ == "__main__":
    main()