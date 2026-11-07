"""
AutoSMS Framework - Módulo Generador de Documentos Académicos (DocBuilder)
========================================================================
Construye automáticamente un borrador formal en Microsoft Word (.docx)
con tipografía académica estandarizada (Times New Roman 10pt, justificado),
tablas unificadas (#666666 / #F0F4F8), diagrama PRISMA tabulado, mapeo
taxonómico y la estructura de Discusión Cualitativa con los papers seleccionados.
"""

import os
import json
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

TEXTS = {
    "es": {
        "abstract": "El presente estudio reporta un Mapeo Sistemático de la Literatura (SMS) conducido bajo las directrices PRISMA 2020. "
                    "Se aplicó un pipeline computacional no supervisado basado en modelos de lenguaje denso (Sentence-Transformers) y "
                    "extracción léxica diferencial (c-TF-IDF), acoplado con supervisión experta continua (Human-in-the-Loop) para categorizar "
                    "el estado del arte, identificar vacíos de investigación y sintetizar evidencias empíricas.",
        "intro": "La creciente proliferación de literatura científica en esta disciplina exige metodologías sistemáticas y reproducibles "
                 "capaces de caracterizar el panorama bibliográfico sin sesgos de selección manual. "
                 "Para guiar esta investigación, se formularon las siguientes Preguntas de Investigación (RQs):",
        "method": "El proceso de selección bibliográfica siguió el estándar internacional PRISMA 2020 (Preferred Reporting Items for Systematic "
                  "Reviews and Meta-Analyses), combinando recolección automatizada de metadatos, deduplicación algorítmica y filtrado temático experto.",
        "results": "El agrupamiento vectorial no supervisado acoplado a c-TF-IDF y el análisis de trayectorias temporales "
                   "permitieron caracterizar la estructura temática del corpus y su tasa de crecimiento anual compuesta (CAGR).",
        "results_note": "Como se observa en la tabla precedente, los tópicos catalogados como 'Emergentes' (🚀) exhiben una marcada aceleración "
                        "en su volumen de publicaciones en los últimos 3 años (CAGR > 12%), reflejando las líneas de frontera investigativa. "
                        "Por su parte, los tópicos 'Maduros' (⚖️) representan los fundamentos metodológicos consolidados de la disciplina.",
        "discussion": "Para complementar la visión macroscópica del mapeo, se realizó un análisis cualitativo a texto completo "
                      "sobre una muestra intencional estratificada de artículos representativos (medoides y publicaciones de alto impacto). "
                      "Esta síntesis responde a las metodologías empíricas y vacíos planteados en las RQs.",
        "threats": {
            "construction": "Sesgo de cobertura en fuentes bibliográficas y sensibilidad de las consultas de búsqueda.",
            "internal": "Posibles sesgos en la interpretación humana durante el nombramiento de clusters y selección de papers para la discusión profunda.",
            "external": "Generalizabilidad de los patrones taxonómicos a entornos industriales no documentados formalmente en la literatura indexada.",
        },
        "conclusions": "El mapeo sistemático ha permitido sintetizar de manera estructurada y auditable el estado del arte en el dominio. "
                       "La integración de modelos de lenguaje densos con supervisión humana experta ofreció un balance óptimo entre "
                       "exhaustividad de cobertura y precisión interpretativa, identificando oportunidades prometedoras para futuras investigaciones.",
        "headings": {
            "intro": "I. INTRODUCCIÓN",
            "method": "II. METODOLOGÍA Y PROTOCOLO PRISMA",
            "results": "III. RESULTADOS: TAXONOMÍA Y DINÁMICA TEMPORAL",
            "discussion": "IV. DISCUSIÓN Y SÍNTESIS CUALITATIVA",
            "threats": "V. AMENAZAS A LA VALIDEZ",
            "conclusions": "VI. CONCLUSIONES Y TRABAJO FUTURO",
            "matrix": "Matriz de Artículos Analizados a Texto Completo",
        },
        "prisma_headers": ["Fase PRISMA", "Descripción del Proceso", "Registros", "Criterio Aplicado"],
        "prisma_rows": [
            ("1. Identificación", "Búsqueda automatizada en fuentes académicas abiertas (OpenAlex)", "Consultas booleanas estructuradas"),
            ("2. Deduplicación", "Fusión de registros redundantes mediante DOI y hashes alfanuméricos", "Normalización estricta de títulos y DOIs"),
            ("3. Screening Temático", "Agrupamiento vectorial y evaluación humana de relevancia", "Criterios de inclusión/exclusión del protocolo"),
            ("4. Inclusión Final", "Corpus consolidado analizado en el mapeo conceptual y discusión", "Aptos para síntesis cuantitativa y cualitativa"),
        ],
        "tax_headers": ["ID", "Taxonomía / Tópico Descubierto", "Artículos", "%", "Dinámica y CAGR", "Descriptores Léxicos (c-TF-IDF)"],
        "sel_headers": ["Ref", "Artículo / Autores", "Año | Citas", "Tópico", "Técnica / Aporte Principal"],
        "abstract_label": "Resumen— ",
        "excluded": " [Excluido]",
        "technique_placeholder": "[Completar técnica y aporte específico]",
        "findings_label": "Hallazgos Empíricos y Limitaciones: ",
        "abstract_prefix": "Síntesis del Abstract: ",
        "findings_space": "[Espacio para el investigador]: Describir aquí los hallazgos empíricos clave de este estudio en relación con {rq}. "
                          "Evaluar el rigor de su validación experimental y las limitaciones identificadas por los autores.",
        "threats_labels": {
            "construction": "• Validez de Construcción: ",
            "internal": "• Validez Interna: ",
            "external": "• Validez Externa: ",
        },
    },
    "en": {
        "abstract": "This study reports a Systematic Literature Review (SLR) conducted under PRISMA 2020 guidelines. "
                    "An unsupervised computational pipeline based on dense language models (Sentence-Transformers) and "
                    "differential lexical extraction (c-TF-IDF) was applied, coupled with continuous expert supervision (Human-in-the-Loop) "
                    "to categorize the state of the art, identify research gaps, and synthesize empirical evidence.",
        "intro": "The growing proliferation of scientific literature in this discipline demands systematic and reproducible methodologies "
                 "capable of characterizing the bibliographic landscape without manual selection bias. "
                 "To guide this research, the following Research Questions (RQs) were formulated:",
        "method": "The bibliographic selection process followed the international PRISMA 2020 standard (Preferred Reporting Items for Systematic "
                  "Reviews and Meta-Analyses), combining automated metadata harvesting, algorithmic deduplication, and expert thematic filtering.",
        "results": "Unsupervised vector clustering coupled with c-TF-IDF and temporal trajectory analysis "
                   "allowed characterization of the thematic structure of the corpus and its compound annual growth rate (CAGR).",
        "results_note": "As shown in the preceding table, topics classified as 'Emerging' (🚀) exhibit a marked acceleration "
                        "in publication volume over the last 3 years (CAGR > 12%), reflecting frontier research lines. "
                        "Meanwhile, 'Mature' (⚖️) topics represent the consolidated methodological foundations of the discipline.",
        "discussion": "To complement the macroscopic view of the mapping, a full-text qualitative analysis was conducted "
                      "on a purposive stratified sample of representative articles (medoids and high-impact publications). "
                      "This synthesis addresses the empirical methodologies and gaps raised in the RQs.",
        "threats": {
            "construction": "Coverage bias in bibliographic sources and sensitivity of search queries.",
            "internal": "Potential biases in human interpretation during cluster naming and paper selection for deep discussion.",
            "external": "Generalizability of taxonomic patterns to industrial environments not formally documented in indexed literature.",
        },
        "conclusions": "The systematic mapping enabled a structured and auditable synthesis of the state of the art in the domain. "
                       "The integration of dense language models with expert human supervision offered an optimal balance between "
                       "coverage exhaustiveness and interpretive accuracy, identifying promising opportunities for future research.",
        "headings": {
            "intro": "I. INTRODUCTION",
            "method": "II. METHODOLOGY AND PRISMA PROTOCOL",
            "results": "III. RESULTS: TAXONOMY AND TEMPORAL DYNAMICS",
            "discussion": "IV. DISCUSSION AND QUALITATIVE SYNTHESIS",
            "threats": "V. THREATS TO VALIDITY",
            "conclusions": "VI. CONCLUSIONS AND FUTURE WORK",
            "matrix": "Matrix of Articles Analyzed in Full Text",
        },
        "prisma_headers": ["PRISMA Phase", "Process Description", "Records", "Criterion Applied"],
        "prisma_rows": [
            ("1. Identification", "Automated search in open academic sources (OpenAlex)", "Structured boolean queries"),
            ("2. Deduplication", "Merging redundant records via DOI and alphanumeric hashes", "Strict normalization of titles and DOIs"),
            ("3. Thematic Screening", "Vector clustering and human relevance evaluation", "Inclusion/exclusion criteria of the protocol"),
            ("4. Final Inclusion", "Consolidated corpus analyzed in conceptual mapping and discussion", "Suitable for quantitative and qualitative synthesis"),
        ],
        "tax_headers": ["ID", "Discovered Taxonomy / Topic", "Articles", "%", "Dynamics and CAGR", "Lexical Descriptors (c-TF-IDF)"],
        "sel_headers": ["Ref", "Article / Authors", "Year | Citations", "Topic", "Technique / Main Contribution"],
        "abstract_label": "Abstract— ",
        "excluded": " [Excluded]",
        "technique_placeholder": "[Complete technique and specific contribution]",
        "findings_label": "Empirical Findings and Limitations: ",
        "abstract_prefix": "Abstract Synthesis: ",
        "findings_space": "[Space for the researcher]: Describe here the key empirical findings of this study in relation to {rq}. "
                          "Evaluate the rigor of its experimental validation and the limitations identified by the authors.",
        "threats_labels": {
            "construction": "• Construct Validity: ",
            "internal": "• Internal Validity: ",
            "external": "• External Validity: ",
        },
    },
}


def set_cell_background(cell, color_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag.endswith('shd'):
            tcPr.remove(child)
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shading_elm)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag.endswith('tcMar'):
            tcPr.remove(child)
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def style_academic_table(table, col_widths=None):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    for row_idx, row in enumerate(table.rows):
        is_header = (row_idx == 0)
        bg_color = "666666" if is_header else ("F0F4F8" if row_idx % 2 == 1 else "FFFFFF")

        for col_idx, cell in enumerate(row.cells):
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=70, bottom=70, left=110, right=110)

            if col_widths and col_idx < len(col_widths):
                cell.width = col_widths[col_idx]

            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.05
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                for run in p.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9)
                    if is_header:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                    else:
                        run.font.color.rgb = RGBColor(30, 30, 30)


class AutoDocBuilder:
    def __init__(self, config: dict):
        self.config = config
        self.meta = config.get("project_metadata", {})
        self.rqs = config.get("research_questions", {})
        self.output_dir = self.meta.get("output_dir", "./output")
        self.title = self.meta.get("title", "Systematic Literature Review")
        self.authors = ", ".join(self.meta.get("authors", ["Principal Investigator"]))
        self.years = self.meta.get("temporal_window", [2018, 2026])
        self.lang = self.meta.get("language", "es")
        self.T = TEXTS.get(self.lang, TEXTS["es"])

    def add_p(self, doc, text="", bold_prefix="", italic=False, space_after=4, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(0)

        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = "Times New Roman"
            r_pre.font.size = Pt(10)
            r_pre.font.bold = True

        if text:
            r = p.add_run(text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.font.italic = italic
        return p

    def add_heading_1(self, doc, title_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(title_text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0, 51, 102)
        return p

    def add_heading_2(self, doc, title_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(title_text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10.5)
        r.font.bold = True
        r.font.italic = True
        r.font.color.rgb = RGBColor(50, 50, 50)
        return p

    def generate_draft(self) -> str:
        print("\n📄 GENERANDO BORRADOR FORMAL EN MICROSOFT WORD (.docx)...")
        doc = docx.Document()

        sections = doc.sections
        for s in sections:
            s.top_margin = Inches(1.0)
            s.bottom_margin = Inches(1.0)
            s.left_margin = Inches(1.0)
            s.right_margin = Inches(1.0)

        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_after = Pt(8)
        r_title = p_title.add_run(self.title)
        r_title.font.name = "Times New Roman"
        r_title.font.size = Pt(16)
        r_title.font.bold = True

        p_sub = doc.add_paragraph()
        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sub.paragraph_format.space_after = Pt(18)
        r_sub = p_sub.add_run(f"{self.authors}\n{self.years[0]} – {self.years[1]}")
        r_sub.font.name = "Times New Roman"
        r_sub.font.size = Pt(10.5)
        r_sub.font.italic = True

        T = self.T
        self.add_p(doc, T["abstract"], bold_prefix=T["abstract_label"])

        self.add_heading_1(doc, T["headings"]["intro"])
        self.add_p(doc, T["intro"])

        for rq_id, rq_desc in self.rqs.items():
            self.add_p(doc, rq_desc, bold_prefix=f"• {rq_id}: ")

        self.add_heading_1(doc, T["headings"]["method"])
        self.add_p(doc, T["method"])

        topics_json_path = os.path.join(self.output_dir, "discovered_topics.json")
        candidates_json_path = os.path.join(self.output_dir, "candidatos_discusion.json")

        topics_info = {}
        if os.path.exists(topics_json_path):
            with open(topics_json_path, "r", encoding="utf-8") as f:
                topics_info = json.load(f)

        candidates = []
        if os.path.exists(candidates_json_path):
            with open(candidates_json_path, "r", encoding="utf-8") as f:
                candidates = json.load(f)

        total_mapped = sum(t.get("count", 0) for t in topics_info.values() if not t.get("exclude_prisma", False))
        total_excluded = sum(t.get("count", 0) for t in topics_info.values() if t.get("exclude_prisma", False))
        total_raw = total_mapped + total_excluded

        t_prisma = doc.add_table(rows=5, cols=4)
        for c_idx, h in enumerate(T["prisma_headers"]):
            t_prisma.rows[0].cells[c_idx].paragraphs[0].text = h

        datos_prisma = [
            ("1. " + ("Identificación" if self.lang == "es" else "Identification"), T["prisma_rows"][0][1], f"N = {total_raw}", T["prisma_rows"][0][2]),
            ("2. " + ("Deduplicación" if self.lang == "es" else "Deduplication"), T["prisma_rows"][1][1], "Filtrado" if self.lang == "es" else "Filtered", T["prisma_rows"][1][2]),
            ("3. " + ("Screening Temático" if self.lang == "es" else "Thematic Screening"), T["prisma_rows"][2][1], f"Excluidos: {total_excluded}" if self.lang == "es" else f"Excluded: {total_excluded}", T["prisma_rows"][2][2]),
            ("4. " + ("Inclusión Final" if self.lang == "es" else "Final Inclusion"), T["prisma_rows"][3][1], f"N = {total_mapped}", T["prisma_rows"][3][2]),
        ]

        for i, row in enumerate(datos_prisma):
            for c_idx in range(4):
                t_prisma.rows[i + 1].cells[c_idx].paragraphs[0].text = row[c_idx]

        style_academic_table(t_prisma, [Inches(1.3), Inches(2.5), Inches(1.1), Inches(1.6)])

        self.add_heading_1(doc, T["headings"]["results"])
        self.add_p(doc, T["results"])

        t_tax = doc.add_table(rows=1 + len(topics_info), cols=6)
        for c_idx, h in enumerate(T["tax_headers"]):
            t_tax.rows[0].cells[c_idx].paragraphs[0].text = h

        for r_idx, (tid, info) in enumerate(sorted(topics_info.items(), key=lambda x: int(x[0]))):
            status = T["excluded"] if info.get("exclude_prisma", False) else ""
            t_dyn = info.get("temporal_dynamics", {})
            badge = t_dyn.get("badge", "")
            cagr = t_dyn.get("cagr_percent", 0.0)

            t_tax.rows[r_idx + 1].cells[0].paragraphs[0].text = str(tid)
            t_tax.rows[r_idx + 1].cells[1].paragraphs[0].text = f"{info.get('assigned_name')}{status}"
            t_tax.rows[r_idx + 1].cells[2].paragraphs[0].text = str(info.get("count", 0))
            t_tax.rows[r_idx + 1].cells[3].paragraphs[0].text = f"{info.get('percentage', 0)}%"
            t_tax.rows[r_idx + 1].cells[4].paragraphs[0].text = f"{badge} ({cagr:+.1f}%)"
            t_tax.rows[r_idx + 1].cells[5].paragraphs[0].text = ", ".join(info.get("keywords", [])[:5])

        style_academic_table(t_tax, [Inches(0.4), Inches(2.0), Inches(0.7), Inches(0.5), Inches(1.4), Inches(1.5)])

        self.add_p(doc, T["results_note"], italic=True)

        self.add_heading_1(doc, T["headings"]["discussion"])
        self.add_p(doc, T["discussion"])

        selected_papers = [c for c in candidates if c.get("selected_for_deep_review", False)]
        if not selected_papers and candidates:
            selected_papers = [c for c in candidates if c.get("rank_in_topic", 1) == 1]

        self.add_heading_2(doc, T["headings"]["matrix"])
        t_sel = doc.add_table(rows=1 + len(selected_papers), cols=5)
        for c_idx, h in enumerate(T["sel_headers"]):
            t_sel.rows[0].cells[c_idx].paragraphs[0].text = h

        for p_idx, p_data in enumerate(selected_papers):
            t_sel.rows[p_idx + 1].cells[0].paragraphs[0].text = f"P{p_idx + 1}"
            t_sel.rows[p_idx + 1].cells[1].paragraphs[0].text = f"{p_data.get('title')}\n({str(p_data.get('authors'))[:40]}...)"
            t_sel.rows[p_idx + 1].cells[2].paragraphs[0].text = f"{p_data.get('publication_year')} | {p_data.get('cited_by_count')} citas" if self.lang == "es" else f"{p_data.get('publication_year')} | {p_data.get('cited_by_count')} citations"
            t_sel.rows[p_idx + 1].cells[3].paragraphs[0].text = str(p_data.get("topic_name"))[:25]
            t_sel.rows[p_idx + 1].cells[4].paragraphs[0].text = T["technique_placeholder"]

        style_academic_table(t_sel, [Inches(0.5), Inches(2.6), Inches(1.0), Inches(1.1), Inches(1.3)])

        for p_idx, p_data in enumerate(selected_papers):
            self.add_heading_2(doc, f"{'Análisis' if self.lang == 'es' else 'Analysis'} de P{p_idx + 1}: {p_data.get('title')}")
            self.add_p(doc, f"Autores: {p_data.get('authors')} ({p_data.get('publication_year')}). " if self.lang == "es" else f"Authors: {p_data.get('authors')} ({p_data.get('publication_year')}). " +
                       f"Publicado en: {p_data.get('venue')}. DOI: {p_data.get('doi')}" if self.lang == "es" else f"Published in: {p_data.get('venue')}. DOI: {p_data.get('doi')}")
            self.add_p(doc, p_data.get('abstract', ''), bold_prefix=T["abstract_prefix"], italic=True)
            rq0 = list(self.rqs.keys())[0] if self.rqs else ("las RQs" if self.lang == "es" else "the RQs")
            self.add_p(doc, T["findings_space"].format(rq=rq0), bold_prefix=T["findings_label"])

        self.add_heading_1(doc, T["headings"]["threats"])
        self.add_p(doc, T["threats"]["construction"], bold_prefix=T["threats_labels"]["construction"])
        self.add_p(doc, T["threats"]["internal"], bold_prefix=T["threats_labels"]["internal"])
        self.add_p(doc, T["threats"]["external"], bold_prefix=T["threats_labels"]["external"])

        self.add_heading_1(doc, T["headings"]["conclusions"])
        self.add_p(doc, T["conclusions"])

        out_docx = os.path.join(self.output_dir, f"{self.meta.get('short_name', 'Systematic_Mapping')}_BORRADOR.docx")
        try:
            doc.save(out_docx)
            print(f"✔ Documento Word formal guardado exitosamente en: {out_docx}")
            return out_docx
        except PermissionError:
            fallback = os.path.join(self.output_dir, f"{self.meta.get('short_name', 'Systematic_Mapping')}_BORRADOR_NUEVO.docx")
            doc.save(fallback)
            print(f"⚠️ El archivo original estaba abierto en Word. Guardado en fallback: {fallback}")
            return fallback