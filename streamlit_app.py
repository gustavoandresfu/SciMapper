"""Optional Streamlit demo for SciMapper.

Install with: pip install 'scimapper[web]'
Run with: streamlit run streamlit_app.py
"""

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover
    raise SystemExit("Streamlit is not installed. Install with: pip install 'scimapper[web]'") from exc

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import load_config, cmd_run_discovery, cmd_compile, cmd_build_doc


def main():
    st.set_page_config(page_title="SciMapper", layout="wide")
    st.title("SciMapper - Systematic Mapping Demo")

    config_path = st.text_input("Config JSON path", value="sms_config.json")
    uploaded = st.file_uploader("Or upload a config JSON", type=["json"])

    cfg = None
    if uploaded is not None:
        cfg = json.load(uploaded)
        st.json(cfg)
    elif os.path.exists(config_path):
        try:
            cfg = load_config(config_path)
            st.success(f"Loaded {config_path}")
        except SystemExit:
            st.error("Invalid or missing config.")

    if cfg is None:
        st.info("Provide a valid config to run the pipeline.")
        return

    col1, col2, col3 = st.columns(3)
    if col1.button("Run discovery"):
        with st.spinner("Running discovery..."):
            cmd_run_discovery(cfg, config_path if os.path.exists(config_path) else "sms_config.json")
        st.success("Discovery finished.")
    if col2.button("Compile"):
        with st.spinner("Compiling..."):
            cmd_compile(cfg)
        st.success("Compilation finished.")
    if col3.button("Build doc"):
        with st.spinner("Building doc..."):
            cmd_build_doc(cfg)
        st.success("Document generated.")


if __name__ == "__main__":
    main()