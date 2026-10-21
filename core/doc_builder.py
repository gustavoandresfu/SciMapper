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

def set_cell_background(cell, color_hex: str):
    """Asigna color de fondo a una celda de tabla."""
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag.endswith('shd'):
            tcPr.remove(child)
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shading_elm)

def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    """Establece márgenes internos (padding) de la celda en dxa."""
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
    """Aplica formato visual académico uniforme a cualquier tabla."""
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
        self.title = self.meta.get("title", "Mapeo Sistemático de la Literatura")
        self.authors = ", ".join(self.meta.get("authors", ["Investigador Principal"]))
        self.years = self.meta.get("temporal_window", [2018, 2026])

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

        # Configuración de márgenes estándar (2.5 cm)
        sections = doc.sections
        for s in sections:
            s.top_margin = Inches(1.0)
            s.bottom_margin = Inches(1.0)
            s.left_margin = Inches(1.0)
            s.right_margin = Inches(1.0)

        # 1. Título y Metadatos
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
        r_sub = p_sub.add_run(f"{self.authors}\nVentana de Estudio: {self.years[0]} – {self.years[1]}")
        r_sub.font.name = "Times New Roman"
        r_sub.font.size = Pt(10.5)
        r_sub.font.italic = True

        # Resumen / Abstract
        self.add_p(doc, 
            f"El presente estudio reporta un Mapeo Sistemático de la Literatura (SMS) conducido bajo las directrices PRISMA 2020. "
            f"Se aplicó un pipeline computacional no supervisado basado en modelos de lenguaje denso (Sentence-Transformers) y "
            f"extracción léxica diferencial (c-TF-IDF), acoplado con supervisión experta continua (Human-in-the-Loop) para categorizar "
            f"el estado del arte, identificar vacíos de investigación y sintetizar evidencias empíricas.",
            bold_prefix="Resumen— ")

        # 2. SECCIÓN I: INTRODUCCIÓN
        self.add_heading_1(doc, "I. INTRODUCCIÓN")
        self.add_p(doc, 
            "La creciente proliferación de literatura científica en esta disciplina exige metodologías sistemáticas y reproducibles "
            "capaces de caracterizar el panorama bibliográfico sin sesgos de selección manual. "
            "Para guiar esta investigación, se formularon las siguientes Preguntas de Investigación (RQs):")

        for rq_id, rq_desc in self.rqs.items():
            self.add_p(doc, rq_desc, bold_prefix=f"• {rq_id}: ")

        # 3. SECCIÓN II: METODOLOGÍA Y FLUJO PRISMA 2020
        self.add_heading_1(doc, "II. METODOLOGÍA Y PROTOCOLO PRISMA")
        self.add_p(doc, 
            "El proceso de selección bibliográfica siguió el estándar internacional PRISMA 2020 (Preferred Reporting Items for Systematic "
            "Reviews and Meta-Analyses), combinando recolección automatizada de metadatos, deduplicación algorítmica y filtrado temático experto.")

        # Cargar datos de tópicos y candidatos
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

        # Tabla PRISMA
        t_prisma = doc.add_table(rows=5, cols=4)
        t_prisma.rows[0].cells[0].paragraphs[0].text = "Fase PRISMA"
        t_prisma.rows[0].cells[1].paragraphs[0].text = "Descripción del Proceso"
        t_prisma.rows[0].cells[2].paragraphs[0].text = "Registros"
        t_prisma.rows[0].cells[3].paragraphs[0].text = "Criterio Aplicado"

        datos_prisma = [
            ("1. Identificación", "Búsqueda automatizada en fuentes académicas abiertas (OpenAlex)", f"N = {total_raw}", "Consultas booleanas estructuradas"),
            ("2. Deduplicación", "Fusión de registros redundantes mediante DOI y hashes alfanuméricos", f"Filtrado", "Normalización estricta de títulos y DOIs"),
            ("3. Screening Temático", "Agrupamiento vectorial y evaluación humana de relevancia", f"Excluidos: {total_excluded}", "Criterios de inclusión/exclusión del protocolo"),
            ("4. Inclusión Final", "Corpus consolidado analizado en el mapeo conceptual y discusión", f"N = {total_mapped}", "Aptos para síntesis cuantitativa y cualitativa")
        ]

        for i, row in enumerate(datos_prisma):
            for c_idx in range(4):
                t_prisma.rows[i+1].cells[c_idx].paragraphs[0].text = row[c_idx]

        style_academic_table(t_prisma, [Inches(1.3), Inches(2.5), Inches(1.1), Inches(1.6)])

        # 4. SECCIÓN III: RESULTADOS Y TAXONOMÍA DEL MAPEO
        self.add_heading_1(doc, "III. RESULTADOS: TAXONOMÍA Y DINÁMICA TEMPORAL")
        self.add_p(doc, 
            "El agrupamiento vectorial no supervisado acoplado a c-TF-IDF y el análisis de trayectorias temporales "
            "permitieron caracterizar la estructura temática del corpus y su tasa de crecimiento anual compuesta (CAGR).")

        # Tabla de Taxonomías con Dinámica Temporal
        t_tax = doc.add_table(rows=1 + len(topics_info), cols=6)
        t_tax.rows[0].cells[0].paragraphs[0].text = "ID"
        t_tax.rows[0].cells[1].paragraphs[0].text = "Taxonomía / Tópico Descubierto"
        t_tax.rows[0].cells[2].paragraphs[0].text = "Artículos"
        t_tax.rows[0].cells[3].paragraphs[0].text = "%"
        t_tax.rows[0].cells[4].paragraphs[0].text = "Dinámica y CAGR"
        t_tax.rows[0].cells[5].paragraphs[0].text = "Descriptores Léxicos (c-TF-IDF)"

        for r_idx, (tid, info) in enumerate(sorted(topics_info.items(), key=lambda x: int(x[0]))):
            status = " [Excluido]" if info.get("exclude_prisma", False) else ""
            t_dyn = info.get("temporal_dynamics", {})
            badge = t_dyn.get("badge", "⚖️ Maduro")
            cagr = t_dyn.get("cagr_percent", 0.0)

            t_tax.rows[r_idx+1].cells[0].paragraphs[0].text = str(tid)
            t_tax.rows[r_idx+1].cells[1].paragraphs[0].text = f"{info.get('assigned_name')}{status}"
            t_tax.rows[r_idx+1].cells[2].paragraphs[0].text = str(info.get("count", 0))
            t_tax.rows[r_idx+1].cells[3].paragraphs[0].text = f"{info.get('percentage', 0)}%"
            t_tax.rows[r_idx+1].cells[4].paragraphs[0].text = f"{badge} ({cagr:+.1f}%)"
            t_tax.rows[r_idx+1].cells[5].paragraphs[0].text = ", ".join(info.get("keywords", [])[:5])

        style_academic_table(t_tax, [Inches(0.4), Inches(2.0), Inches(0.7), Inches(0.5), Inches(1.4), Inches(1.5)])

        self.add_p(doc, 
            "Como se observa en la tabla precedente, los tópicos catalogados como 'Emergentes' (🚀) exhiben una marcada aceleración "
            "en su volumen de publicaciones en los últimos 3 años (CAGR > 12%), reflejando las líneas de frontera investigativa. "
            "Por su parte, los tópicos 'Maduros' (⚖️) representan los fundamentos metodológicos consolidados de la disciplina.",
            italic=True)

        # 5. SECCIÓN IV: DISCUSIÓN CUALITATIVA
        self.add_heading_1(doc, "IV. DISCUSIÓN Y SÍNTESIS CUALITATIVA")
        self.add_p(doc, 
            "Para complementar la visión macroscópica del mapeo, se realizó un análisis cualitativo a texto completo "
            "sobre una muestra intencional estratificada de artículos representativos (medoides y publicaciones de alto impacto). "
            "Esta síntesis responde a las metodologías empíricas y vacíos planteados en las RQs.")

        selected_papers = [c for c in candidates if c.get("selected_for_deep_review", False)]
        if not selected_papers and candidates:
            # Si el usuario no marcó ninguno aún, tomar el top 1 de cada tópico
            selected_papers = [c for c in candidates if c.get("rank_in_topic", 1) == 1]

        # Tabla de Artículos Seleccionados
        self.add_heading_2(doc, "Matriz de Artículos Analizados a Texto Completo")
        t_sel = doc.add_table(rows=1 + len(selected_papers), cols=5)
        t_sel.rows[0].cells[0].paragraphs[0].text = "Ref"
        t_sel.rows[0].cells[1].paragraphs[0].text = "Artículo / Autores"
        t_sel.rows[0].cells[2].paragraphs[0].text = "Año | Citas"
        t_sel.rows[0].cells[3].paragraphs[0].text = "Tópico"
        t_sel.rows[0].cells[4].paragraphs[0].text = "Técnica / Aporte Principal"

        for p_idx, p_data in enumerate(selected_papers):
            t_sel.rows[p_idx+1].cells[0].paragraphs[0].text = f"P{p_idx+1}"
            t_sel.rows[p_idx+1].cells[1].paragraphs[0].text = f"{p_data.get('title')}\n({p_data.get('authors')[:40]}...)"
            t_sel.rows[p_idx+1].cells[2].paragraphs[0].text = f"{p_data.get('publication_year')} | {p_data.get('cited_by_count')} citas"
            t_sel.rows[p_idx+1].cells[3].paragraphs[0].text = str(p_data.get("topic_name"))[:25]
            t_sel.rows[p_idx+1].cells[4].paragraphs[0].text = "[Completar técnica y aporte específico]"

        style_academic_table(t_sel, [Inches(0.5), Inches(2.6), Inches(1.0), Inches(1.1), Inches(1.3)])

        # Subsecciones por artículo para redactar hallazgos
        for p_idx, p_data in enumerate(selected_papers):
            self.add_heading_2(doc, f"Análisis de P{p_idx+1}: {p_data.get('title')}")
            self.add_p(doc, f"Autores: {p_data.get('authors')} ({p_data.get('publication_year')}). Publicado en: {p_data.get('venue')}. DOI: {p_data.get('doi')}")
            self.add_p(doc, p_data.get('abstract', ''), bold_prefix="Síntesis del Abstract: ", italic=True)
            self.add_p(doc, 
                f"[Espacio para el investigador]: Describir aquí los hallazgos empíricos clave de este estudio en relación con {list(self.rqs.keys())[0] if self.rqs else 'las RQs'}. "
                f"Evaluar el rigor de su validación experimental y las limitaciones identificadas por los autores.",
                bold_prefix="Hallazgos Empíricos y Limitaciones: ")

        # 6. SECCIÓN V: AMENAZAS A LA VALIDEZ
        self.add_heading_1(doc, "V. AMENAZAS A LA VALIDEZ")
        self.add_p(doc, "Sesgo de cobertura en fuentes bibliográficas y sensibilidad de las consultas de búsqueda.", bold_prefix="• Validez de Construcción: ")
        self.add_p(doc, "Posibles sesgos en la interpretación humana durante el nombramiento de clusters y selección de papers para la discusión profunda.", bold_prefix="• Validez Interna: ")
        self.add_p(doc, "Generalizabilidad de los patrones taxonómicos a entornos industriales no documentados formalmente en la literatura indexada.", bold_prefix="• Validez Externa: ")

        # 7. SECCIÓN VI: CONCLUSIONES
        self.add_heading_1(doc, "VI. CONCLUSIONES Y TRABAJO FUTURO")
        self.add_p(doc, 
            "El mapeo sistemático ha permitido sintetizar de manera estructurada y auditable el estado del arte en el dominio. "
            "La integración de modelos de lenguaje densos con supervisión humana experta ofreció un balance óptimo entre "
            "exhaustividad de cobertura y precisión interpretativa, identificando oportunidades prometedoras para futuras investigaciones.")

        # Guardar archivo con manejo de fallback
        out_docx = os.path.join(self.output_dir, f"{self.meta.get('short_name', 'Mapeo_Sistematico')}_BORRADOR.docx")
        try:
            doc.save(out_docx)
            print(f"✔ Documento Word formal guardado exitosamente en: {out_docx}")
            return out_docx
        except PermissionError:
            fallback = os.path.join(self.output_dir, f"{self.meta.get('short_name', 'Mapeo_Sistematico')}_BORRADOR_NUEVO.docx")
            doc.save(fallback)
            print(f"⚠️ El archivo original estaba abierto en Word. Guardado en fallback: {fallback}")
            return fallback
