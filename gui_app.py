"""Desktop GUI for SciMapper using CustomTkinter."""

import os
import sys
import json
import threading
import queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
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
    "es": {
        "title": "SciMapper - Asistente de Configuración",
        "welcome": "Bienvenido a SciMapper. Este asistente te guiará paso a paso.",
        "lang": "Idioma",
        "next": "Siguiente ➡",
        "back": "⬅ Anterior",
        "run_discovery": "1) Ejecutar Discovery",
        "compile": "2) Compilar",
        "build_doc": "3) Generar documento",
        "open_folder": "Abrir carpeta de salida",
        "valid": "Configuración válida ✅",
        "invalid": "Configuración inválida",
        "running": "Ejecutando...",
        "done": "Finalizado.",
    },
    "en": {
        "title": "SciMapper - Configuration Wizard",
        "welcome": "Welcome to SciMapper. This wizard will guide you step by step.",
        "lang": "Language",
        "next": "Next ➡",
        "back": "⬅ Back",
        "run_discovery": "1) Run Discovery",
        "compile": "2) Compile",
        "build_doc": "3) Build Doc",
        "open_folder": "Open output folder",
        "valid": "Configuration is valid ✅",
        "invalid": "Invalid configuration",
        "running": "Running...",
        "done": "Done.",
    },
}


def t(key):
    lang = app_state.get("lang", "es")
    return I18N.get(lang, I18N["es"]).get(key, key)


app_state = {
    "lang": "es",
    "cfg": None,
    "step": 0,
    "running": False,
    "log_queue": None,
}


def load_template():
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class SciMapperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SciMapper")
        self.geometry("950x720")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        app_state["cfg"] = load_template()
        app_state["log_queue"] = queue.Queue()

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        self.steps = [
            self.step_welcome,
            self.step_metadata,
            self.step_rqs,
            self.step_search,
            self.step_nlp,
            self.step_synth,
            self.step_review,
        ]

        self.render_step()
        self.poll_logs()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def render_step(self):
        self.clear()
        self.steps[app_state["step"]](self.container)

    def nav_buttons(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=10)
        if app_state["step"] > 0:
            ctk.CTkButton(frame, text=t("back"), command=self.prev_step).pack(side="left", padx=5)
        if app_state["step"] < len(self.steps) - 1:
            ctk.CTkButton(frame, text=t("next"), command=self.next_step).pack(side="right", padx=5)

    def next_step(self):
        app_state["step"] = min(app_state["step"] + 1, len(self.steps) - 1)
        self.render_step()

    def prev_step(self):
        app_state["step"] = max(app_state["step"] - 1, 0)
        self.render_step()

    # ---------- Steps ----------
    def step_welcome(self, parent):
        ctk.CTkLabel(parent, text="SciMapper", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)
        ctk.CTkLabel(parent, text=t("welcome"), font=ctk.CTkFont(size=14)).pack(pady=10)

        lang_frame = ctk.CTkFrame(parent)
        lang_frame.pack(pady=10)
        ctk.CTkLabel(lang_frame, text=t("lang")).pack(side="left", padx=5)
        lang_var = ctk.StringVar(value=app_state["lang"])
        ctk.CTkOptionMenu(lang_frame, values=["es", "en"], variable=lang_var,
                          command=lambda v: self.set_lang(v)).pack(side="left", padx=5)

        self.nav_buttons(parent)

    def set_lang(self, v):
        app_state["lang"] = v
        self.render_step()

    def step_metadata(self, parent):
        ctk.CTkLabel(parent, text="1) Metadatos", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        cfg = app_state["cfg"]
        meta = cfg.setdefault("project_metadata", {})

        self.field(parent, "Título", meta.get("title", ""), lambda v: meta.__setitem__("title", v))
        self.field(parent, "Nombre corto", meta.get("short_name", "SMS_Proyecto"), lambda v: meta.__setitem__("short_name", v))
        authors = self.field(parent, "Autores (coma)", ", ".join(meta.get("authors", [])), lambda v: meta.__setitem__("authors", [a.strip() for a in v.split(",") if a.strip()]))

        years = meta.get("temporal_window", [2018, 2026])
        self.field(parent, "Año inicial", str(years[0]), lambda v: meta.__setitem__("temporal_window", [int(v), meta.get("temporal_window", [2018, 2026])[1]]))
        self.field(parent, "Año final", str(years[1]), lambda v: meta.__setitem__("temporal_window", [meta.get("temporal_window", [2018, 2026])[0], int(v)]))

        default_out = f"./output_{meta.get('short_name', 'SMS_Proyecto')}"
        if meta.get("output_dir", "./output") in ("./output", ""):
            meta["output_dir"] = default_out
        self.field(parent, "Carpeta de salida", meta.get("output_dir", default_out), lambda v: meta.__setitem__("output_dir", v))

        self.nav_buttons(parent)

    def step_rqs(self, parent):
        ctk.CTkLabel(parent, text="2) Preguntas de investigación (RQs)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        cfg = app_state["cfg"]
        rqs = cfg.setdefault("research_questions", {})
        for key in ["RQ1", "RQ2", "RQ3"]:
            self.field(parent, key, rqs.get(key, ""), lambda v, k=key: rqs.__setitem__(k, v), height=60)
        self.nav_buttons(parent)

    def step_search(self, parent):
        ctk.CTkLabel(parent, text="3) Estrategia de búsqueda (OpenAlex)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        cfg = app_state["cfg"]
        strat = cfg.setdefault("search_strategy", {})
        self.field(parent, "Email OpenAlex", strat.get("openalex_email", ""), lambda v: strat.__setitem__("openalex_email", v))
        self.field(parent, "Max resultados", str(strat.get("max_results_per_query", 100)), lambda v: strat.__setitem__("max_results_per_query", int(v)))
        queries_box = ctk.CTkTextbox(parent, height=100)
        queries_box.insert("1.0", "\n".join(strat.get("queries", [])))
        queries_box.pack(fill="x", pady=2)
        def update_queries(event=None):
            strat["queries"] = [q.strip() for q in queries_box.get("1.0", "end").splitlines() if q.strip()]
        queries_box.bind("<KeyRelease>", update_queries)
        update_queries()
        self.nav_buttons(parent)

    def step_nlp(self, parent):
        ctk.CTkLabel(parent, text="4) Ajuste NLP", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        cfg = app_state["cfg"]
        nlp = cfg.setdefault("nlp_tuning", {})
        nlp["domain_preset"] = self.combo(parent, "Preset de dominio", list(DOMAIN_PRESETS.keys()), nlp.get("domain_preset", "software_engineering"))
        nlp["domain_presets_catalog"] = DOMAIN_PRESETS
        nlp["embedding_model"] = DOMAIN_PRESETS[nlp["domain_preset"]]
        nlp["n_clusters"] = int(self.field(parent, "Número de clusters", str(nlp.get("n_clusters", 6)), lambda v: nlp.__setitem__("n_clusters", int(v))))
        nlp["stop_words"] = self.combo(parent, "Stop words", ["english", "spanish", "multilingual", "none"], nlp.get("stop_words", "english"))
        nlp["dimensionality_reduction"] = self.combo(parent, "Reducción", ["pca_tsne", "pca"], nlp.get("dimensionality_reduction", "pca_tsne"))
        self.nav_buttons(parent)

    def step_synth(self, parent):
        ctk.CTkLabel(parent, text="5) Síntesis cualitativa", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        cfg = app_state["cfg"]
        synth = cfg.setdefault("qualitative_synthesis", {})
        synth["candidates_per_topic"] = int(self.field(parent, "Candidatos por tópico", str(synth.get("candidates_per_topic", 3)), lambda v: synth.__setitem__("candidates_per_topic", int(v))))
        synth["min_citations"] = int(self.field(parent, "Umbral mínimo de citas", str(synth.get("min_citations", 1)), lambda v: synth.__setitem__("min_citations", int(v))))
        self.nav_buttons(parent)

    def step_review(self, parent):
        ctk.CTkLabel(parent, text="6) Revisión y ejecución", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        cfg = app_state["cfg"]
        errors = validate_config(cfg)
        if errors:
            ctk.CTkLabel(parent, text=t("invalid"), text_color="red").pack()
            for e in errors:
                ctk.CTkLabel(parent, text=f"- {e}").pack()
        else:
            ctk.CTkLabel(parent, text=t("valid"), text_color="green").pack()

        btn_frame = ctk.CTkFrame(parent)
        btn_frame.pack(pady=10)
        self.btn_discovery = ctk.CTkButton(btn_frame, text=t("run_discovery"), command=lambda: self.run_task("discovery"))
        self.btn_discovery.pack(side="left", padx=5)
        self.btn_compile = ctk.CTkButton(btn_frame, text=t("compile"), command=lambda: self.run_task("compile"))
        self.btn_compile.pack(side="left", padx=5)
        self.btn_build = ctk.CTkButton(btn_frame, text=t("build_doc"), command=lambda: self.run_task("build_doc"))
        self.btn_build.pack(side="left", padx=5)

        ctk.CTkButton(parent, text=t("open_folder"), command=self.open_folder).pack(pady=5)

        self.progress = ctk.CTkProgressBar(parent)
        self.progress.pack(fill="x", pady=5)
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(parent, height=220)
        self.log_box.pack(fill="both", expand=True, pady=5)

        self.nav_buttons(parent)

    # ---------- Helpers ----------
    def field(self, parent, label, default, on_change=None, height=None):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=3)
        ctk.CTkLabel(frame, text=label, width=200, anchor="w").pack(side="left", padx=5)
        var = ctk.StringVar(value=str(default))
        if on_change:
            var.trace_add("write", lambda *a: on_change(var.get()))
        e = ctk.CTkEntry(frame, textvariable=var)
        e.pack(side="left", fill="x", expand=True, padx=5)
        return var.get()

    def textbox(self, parent, label, default):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", pady=2)
        tbox = ctk.CTkTextbox(parent, height=80)
        tbox.insert("1.0", str(default))
        tbox.pack(fill="x", pady=2)
        # store reference for reading later (read on run)
        self._last_textbox = tbox
        return tbox.get("1.0", "end").strip()

    def combo(self, parent, label, values, default):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=3)
        ctk.CTkLabel(frame, text=label, width=200, anchor="w").pack(side="left", padx=5)
        var = ctk.StringVar(value=default if default in values else values[0])
        c = ctk.CTkOptionMenu(frame, values=values, variable=var)
        c.pack(side="left", padx=5)
        return var.get()

    def run_task(self, task):
        if app_state["running"]:
            return
        app_state["running"] = True
        self.set_buttons_state("disabled")
        self.progress.set(0.2)
        self.log(">> " + task)
        cfg = app_state["cfg"]
        config_path = "sms_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        # Read textbox queries from step_search if present (already bound via cfg)
        def worker():
            import io
            import contextlib

            class Writer(io.StringIO):
                def write(self, s):
                    if s.strip():
                        app_state["log_queue"].put(s.strip())
                    return len(s)

            buf = Writer()
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    if task == "discovery":
                        cmd_run_discovery(cfg, config_path)
                    elif task == "compile":
                        cmd_compile(cfg)
                    elif task == "build_doc":
                        cmd_build_doc(cfg)
                app_state["log_queue"].put("__DONE__")
            except Exception as e:
                app_state["log_queue"].put(f"ERROR: {e}")
                app_state["log_queue"].put("__DONE__")

        threading.Thread(target=worker, daemon=True).start()

    def poll_logs(self):
        try:
            while True:
                msg = app_state["log_queue"].get_nowait()
                if msg == "__DONE__":
                    app_state["running"] = False
                    self.set_buttons_state("normal")
                    self.progress.set(1.0)
                    self.log(">> " + t("done"))
                else:
                    self.log(msg)
        except queue.Empty:
            pass
        self.after(200, self.poll_logs)

    def log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def set_buttons_state(self, state):
        for b in (self.btn_discovery, self.btn_compile, self.btn_build):
            b.configure(state=state)

    def open_folder(self):
        cfg = app_state["cfg"]
        out = cfg.get("project_metadata", {}).get("output_dir", "./output")
        out = os.path.abspath(out)
        if not os.path.exists(out):
            os.makedirs(out, exist_ok=True)
        os.startfile(out)


def main():
    app = SciMapperGUI()
    app.mainloop()


if __name__ == "__main__":
    main()