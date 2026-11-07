"""
AutoSMS Framework - Módulo de Visualización Avanzada (Visualizer)
===============================================================
Construye visualizaciones interactivas de última generación en Plotly:
1. Vista Dual: Mapa Conceptual 2D de Dispersión + Capa de Contorno de Densidad (KDE).
2. Panel Lateral de Evolución Temporal (2018–2026) con cálculo de tasas de crecimiento.
3. Selector interactivo de modos de visualización (Híbrido, Puntos, Densidad Topográfica).
"""

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class AutoVisualizer:
    def __init__(self, config: dict):
        self.config = config
        self.output_dir = config.get("project_metadata", {}).get("output_dir", "./output")
        self.title = config.get("project_metadata", {}).get("title", "Mapeo Sistemático de Literatura")

    def build_interactive_map(self, df: pd.DataFrame, topics_info: dict) -> str:
        print("\n🌐 Construyendo Dashboard Dual Interactivo (Mapa 2D KDE + Trayectorias Temporales)...")

        colores = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
            "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]

        # Crear figura con 2 subplots en paralelo: Mapa 2D (58%) y Líneas Temporales (42%)
        fig = make_subplots(
            rows=1, cols=2,
            column_widths=[0.58, 0.34],
            subplot_titles=[
                "<b>Mapa Semántico 2D (t-SNE + KDE)</b>",
                "<b>Dinámica Temporal Anual</b>"
            ],
            horizontal_spacing=0.08
        )

        # 1. Capa Base: Mapa de Contorno / Densidad (KDE 2D)
        kde_trace = go.Histogram2dContour(
            x=df["coord_x"],
            y=df["coord_y"],
            name="Densidad Topográfica (KDE)",
            colorscale="Blues",
            reversescale=False,
            showscale=False,
            ncontours=22,
            opacity=0.30,
            hoverinfo="skip"
        )
        fig.add_trace(kde_trace, row=1, col=1)

        # 2. Capas de Clusters (Envolventes Convexas, Puntos y Centroides)
        from scipy.spatial import ConvexHull

        def hex_to_rgb(hex_str):
            hex_str = hex_str.lstrip('#')
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

        unique_topics = sorted(df["topic_id"].unique())
        total_docs = len(df)
        hull_trace_indices = []
        scatter_trace_indices = []
        centroid_trace_indices = []

        for idx, tid in enumerate(unique_topics):
            sub = df[df["topic_id"] == tid]
            color = colores[idx % len(colores)]
            r, g, b = hex_to_rgb(color)
            t_info = topics_info.get(str(tid), topics_info.get(tid, {}))
            t_name = t_info.get("assigned_name", f"Tópico {tid}")
            
            # Dinámica temporal para tooltip
            t_dyn = t_info.get("temporal_dynamics", {})
            badge = t_dyn.get("badge", "⚖️ Maduro")
            cagr = t_dyn.get("cagr_percent", 0.0)
            kws = ", ".join(t_info.get("keywords", [])[:5])

            pts = sub[["coord_x", "coord_y"]].values
            center = np.mean(pts, axis=0)
            cx, cy = float(center[0]), float(center[1])

            # A. Envolvente Convexa del Cluster
            dists = np.linalg.norm(pts - center, axis=1)
            mask_core = dists <= np.percentile(dists, 92)
            pts_core = pts[mask_core]

            if len(pts_core) >= 3:
                hull = ConvexHull(pts_core)
                hull_pts = pts_core[hull.vertices]
                hull_pts = np.vstack([hull_pts, hull_pts[0]])
                hx = hull_pts[:, 0]
                hy = hull_pts[:, 1]
            else:
                hx = [cx]
                hy = [cy]

            hull_trace = go.Scatter(
                x=hx,
                y=hy,
                mode="lines",
                fill="toself",
                fillcolor=f"rgba({r}, {g}, {b}, 0.16)",
                line=dict(color=f"rgba({r}, {g}, {b}, 0.85)", width=2, dash="dash", shape="spline", smoothing=1.3),
                name=f"Área {badge} {t_name}",
                legendgroup=f"topic_{tid}",
                showlegend=False,
                hoverinfo="skip"
            )
            fig.add_trace(hull_trace, row=1, col=1)
            hull_trace_indices.append(len(fig.data) - 1)

            # B. Puntos individuales
            hover_texts = []
            for _, r_doc in sub.iterrows():
                snip = (r_doc['abstract'][:240] + "...") if len(r_doc['abstract']) > 240 else r_doc['abstract']
                txt = (
                    f"<b>{r_doc['title']}</b><br>"
                    f"<i>Autores:</i> {r_doc['authors']}<br>"
                    f"<i>Año:</i> {r_doc['publication_year']} | <i>Venue:</i> {r_doc['venue']}<br>"
                    f"<i>Citas:</i> {r_doc.get('cited_by_count', 0)} | <b>Estado:</b> {badge} (CAGR: {cagr}%)<br>"
                    f"<hr style='margin:4px 0;'>"
                    f"<b>Abstract:</b> {snip}"
                )
                hover_texts.append(txt)

            scatter_trace = go.Scatter(
                x=sub["coord_x"],
                y=sub["coord_y"],
                mode="markers",
                name=f"{badge} {t_name} ({len(sub)})",
                text=hover_texts,
                hoverinfo="text",
                legendgroup=f"topic_{tid}",
                marker=dict(size=8, color=color, opacity=0.88, line=dict(width=1, color="#222222"))
            )
            fig.add_trace(scatter_trace, row=1, col=1)
            scatter_trace_indices.append(len(fig.data) - 1)

            # C. Centroide y Etiqueta de Cluster
            centroid_hover = (
                f"<b>🏛️ CLUSTER {tid}: {t_name}</b><br>"
                f"<b>Estado:</b> {badge} (CAGR: {cagr}%)<br>"
                f"<b>Volumen:</b> {len(sub)} artículos ({round(len(sub)/total_docs*100, 1)}%)<br>"
                f"<b>Palabras Clave (c-TF-IDF):</b> {kws}<br>"
                f"<i>Centroide: ({cx:.2f}, {cy:.2f})</i>"
            )

            centroid_trace = go.Scatter(
                x=[cx],
                y=[cy],
                mode="markers+text",
                text=[f"<b>C{tid}</b>"],
                textposition="top center",
                textfont=dict(size=12, color="#0f172a", family="Arial Black, Segoe UI, sans-serif"),
                hovertext=[centroid_hover],
                hoverinfo="text",
                legendgroup=f"topic_{tid}",
                showlegend=False,
                marker=dict(size=16, symbol="diamond", color=color, line=dict(width=2, color="#ffffff"))
            )
            fig.add_trace(centroid_trace, row=1, col=1)
            centroid_trace_indices.append(len(fig.data) - 1)

        # 3. Subplot 2: Evolución Temporal Anual (Líneas de tendencia)
        years_series = pd.to_numeric(df["publication_year"], errors="coerce").dropna().astype(int)
        min_year = int(years_series.min()) if not years_series.empty else 2018
        max_year = int(years_series.max()) if not years_series.empty else 2026
        all_years = list(range(min_year, max_year + 1))

        for idx, tid in enumerate(unique_topics):
            color = colores[idx % len(colores)]
            t_info = topics_info.get(str(tid), topics_info.get(tid, {}))
            t_name = t_info.get("assigned_name", f"Tópico {tid}")
            t_dyn = t_info.get("temporal_dynamics", {})
            y_dist = t_dyn.get("yearly_distribution", {})

            y_values = [y_dist.get(y, y_dist.get(str(y), 0)) for y in all_years]

            line_trace = go.Scatter(
                x=all_years,
                y=y_values,
                mode="lines+markers",
                name=f"{t_name}",
                legendgroup=f"topic_{tid}",
                showlegend=False,
                line=dict(color=color, width=2.8),
                marker=dict(size=7, color=color),
                hovertemplate=f"<b>{t_name}</b><br>Año %{{x}}: %{{y}} artículos<extra></extra>"
            )
            fig.add_trace(line_trace, row=1, col=2)

        # 4. Botones de Control para Alternar Modos de Visualización (Updatemenus)
        total_traces = len(fig.data)
        
        vis_all = [True] * total_traces
        vis_regions = [True] * total_traces
        for p_idx in scatter_trace_indices:
            vis_regions[p_idx] = False
            
        vis_points = [False] * total_traces
        for p_idx in scatter_trace_indices + centroid_trace_indices:
            vis_points[p_idx] = True
        for l_idx in range(len(fig.data) - len(unique_topics), len(fig.data)):
            vis_points[l_idx] = True

        fig.add_annotation(
            x=0.02,
            y=1.30,
            xref="paper",
            yref="paper",
            text=f"<b>{self.title}</b><br><span style='font-size:13px; color:#64748B; font-weight:normal;'>Mapeo Semántico 2D (t-SNE) + Densidad Topográfica (KDE) + Radar de Dinámica Temporal | {len(df)} Artículos Indexados</span>",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(size=17, color="#0F172A", family="Segoe UI, Inter, Arial, sans-serif"),
        )

        fig.update_annotations(
            font=dict(size=11, color="#334155"),
            selector=lambda a: ("Mapa Sem" in (a.text or "")) or ("Dinámica Temporal" in (a.text or "")),
        )

        fig.update_layout(
            autosize=True,
            height=860,
            template="plotly_white",
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    x=0.99,
                    xanchor="right",
                    y=1.18,
                    showactive=True,
                    bgcolor="#F8FAFC",
                    bordercolor="#CBD5E1",
                    font=dict(size=11, color="#1E293B"),
                    buttons=[
                        dict(label="🌟 Vista Completa (Regiones + Puntos + Densidad)", method="update", args=[{"visible": vis_all}]),
                        dict(label="🛡️ Solo Regiones y Fronteras de Clusters", method="update", args=[{"visible": vis_regions}]),
                        dict(label="📍 Solo Puntos de Artículos", method="update", args=[{"visible": vis_points}])
                    ]
                )
            ],
            title={'text': ''},
            xaxis=dict(title="Dimensión Semántica 1 (t-SNE)", showgrid=True, gridcolor="#F1F5F9", zeroline=False),
            yaxis=dict(title="Dimensión Semántica 2 (t-SNE)", showgrid=True, gridcolor="#F1F5F9", zeroline=False),
            xaxis2=dict(
                title="Año de Publicación",
                dtick=1,
                range=[min_year - 0.5, max_year + 0.5],
                showgrid=True,
                gridcolor="#F1F5F9"
            ),
            yaxis2=dict(title="Volumen de Publicaciones (N)", showgrid=True, gridcolor="#F1F5F9"),
            legend=dict(
                title=dict(text="<b>Taxonomías y Estado de Madurez</b>", font=dict(size=12, color="#0F172A")),
                orientation="h",
                y=-0.16,
                x=0.5,
                xanchor="center",
                bgcolor="rgba(255,255,255,0.95)",
                bordercolor="#CBD5E1",
                borderwidth=1,
                font=dict(size=11, color="#334155")
            ),
            margin=dict(l=60, r=50, t=210, b=140)
        )

        out_html = os.path.join(self.output_dir, "mapa_interactivo.html")
        fig.write_html(out_html, config={"responsive": True, "displayModeBar": True})
        print(f"✔ Dashboard Dual interactivo generado en: {out_html}")
        return out_html

    def save_final_dataset(self, df: pd.DataFrame) -> str:
        out_csv = os.path.join(self.output_dir, "corpus_con_topicos.csv")
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        print(f"✔ Dataset consolidado guardado en: {out_csv}")
        return out_csv
