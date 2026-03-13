# analytic.py  —  Analytics page with Plotly dark-theme charts
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

from style_advisor import get_style_advisor

# Plotly layout defaults matching the app palette
_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#f5f0e8"),
    title_font=dict(family="Playfair Display, serif", color="#c9a84c"),
    margin=dict(l=10, r=10, t=50, b=10),
    legend=dict(font=dict(color="#f5f0e8")),
)

_COLOR_SEQ = ["#c9a84c", "#e8c4b8", "#4a90d9", "#6dc9a0", "#d97e6a"]


# ─── Cached heavy computation (PCA + KMeans) ─────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _compute_catalog_data(_client):
    """Fetch vectors, run PCA + KMeans. Cached 5 min to avoid re-running."""
    try:
        pts = _client.scroll(collection_name="fashion_images", with_vectors=True)[0]
    except Exception:
        return None
    if not pts:
        return None
    vecs = [p.vector for p in pts]
    count = len(pts)
    n_clusters = min(5, count)
    pca_result = PCA(n_components=2).fit_transform(vecs)
    cluster_labels = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit_predict(vecs)
    filenames = [p.payload.get("filename", f"Article {i+1}") for i, p in enumerate(pts)]
    return {
        "count": count,
        "pca_x": pca_result[:, 0].tolist(),
        "pca_y": pca_result[:, 1].tolist(),
        "clusters": cluster_labels.tolist(),
        "filenames": filenames,
        "n_clusters": n_clusters,
    }


def _metric_card(label, value, icon=""):
    """Styled HTML metric card."""
    return f"""
    <div class="fa-card" style="text-align:center;padding:1.2rem 0.8rem;">
        <div style="font-size:1.5rem;margin-bottom:4px;">{icon}</div>
        <div style="color:var(--accent);font-size:1.8rem;font-weight:700;
                    font-family:'Playfair Display',serif;">{value}</div>
        <div style="color:var(--muted);font-size:0.82rem;margin-top:2px;">{label}</div>
    </div>
    """


def render(client, model, user_profile, username):
    """Render the Analytics dashboard — cached computation, better layout."""
    advisor = get_style_advisor()

    st.markdown("## Tableau de bord")

    # ─── Cached data ─────────────────────────────────────────────────────
    with st.spinner("Chargement des donnees..."):
        data = _compute_catalog_data(client)

    if data is None:
        st.info("Le catalogue est vide. Lancez le pipeline d'indexation pour commencer.")
        return

    # ─── KPI cards (4 columns) ───────────────────────────────────────────
    n_favs = len(st.session_state.get("favorites", set()))
    profile_fields = ["nom", "prenom", "age", "taille", "teint", "morpho"]
    has_img = bool(user_profile.get("profile_img_b64") or user_profile.get("profile_img_path"))
    pct = int(
        (sum(1 for f in profile_fields if user_profile.get(f)) + (1 if has_img else 0))
        / (len(profile_fields) + 1) * 100
    )
    n_searches = len(st.session_state.get("search_history", []))

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(_metric_card("Articles au catalogue", data["count"], "👗"), unsafe_allow_html=True)
    with k2:
        st.markdown(_metric_card("Favoris sauvegardes", n_favs, "❤️"), unsafe_allow_html=True)
    with k3:
        st.markdown(_metric_card("Profil complete", f"{pct}%", "👤"), unsafe_allow_html=True)
    with k4:
        st.markdown(_metric_card("Recherches (session)", n_searches, "🔍"), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    # ─── Charts: two-column layout ───────────────────────────────────────
    col_bar, col_scatter = st.columns(2)

    with col_bar:
        cluster_counts = pd.Series(data["clusters"]).value_counts().sort_index()
        df_bar = pd.DataFrame({
            "Groupe": [f"Groupe {c+1}" for c in cluster_counts.index],
            "Articles": cluster_counts.values,
        })
        fig_bar = px.bar(
            df_bar, x="Groupe", y="Articles",
            title="Repartition par groupe de style",
            color="Groupe",
            color_discrete_sequence=_COLOR_SEQ,
        )
        fig_bar.update_layout(**_PLOTLY_LAYOUT)
        fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Nombre d'articles")
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_scatter:
        df_scatter = pd.DataFrame({
            "x": data["pca_x"],
            "y": data["pca_y"],
            "Groupe": [f"Groupe {c+1}" for c in data["clusters"]],
            "Article": data["filenames"],
        })
        fig_scatter = px.scatter(
            df_scatter, x="x", y="y",
            color="Groupe",
            hover_name="Article",
            title="Carte du catalogue (projection PCA)",
            color_discrete_sequence=_COLOR_SEQ,
        )
        fig_scatter.update_layout(**_PLOTLY_LAYOUT)
        fig_scatter.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            legend_title_text="",
        )
        fig_scatter.update_traces(marker=dict(size=7, opacity=0.75))
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ─── Style profile + info ────────────────────────────────────────────
    st.divider()
    st.markdown("### Votre profil de style")

    col_radar, col_info = st.columns([3, 2])

    with col_radar:
        search_hist = st.session_state.get("search_history", [])
        hist_text = " ".join(search_hist).lower()

        def _score(keywords):
            return min(10, sum(1 for kw in keywords if kw in hist_text) * 3 + 3)

        radar_axes = {
            "Decontracte": _score(["casual", "jean", "t-shirt", "sneaker", "denim"]),
            "Formel":      _score(["formal", "blazer", "costume", "cravate", "office"]),
            "Colore":      _score(["rouge", "rose", "color", "vif", "jaune", "bright"]),
            "Minimaliste": _score(["noir", "blanc", "simple", "minimal", "basic"]),
            "Sportif":     _score(["sport", "running", "athletic", "sneaker", "trainer"]),
            "Elegant":     _score(["elegant", "soiree", "chic", "satin", "silk"]),
        }

        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=list(radar_axes.values()),
                theta=list(radar_axes.keys()),
                fill="toself",
                fillcolor="rgba(201,168,76,0.15)",
                line=dict(color="#c9a84c", width=2),
                name="Votre style",
            )
        )
        fig_radar.update_layout(
            title="Tendances de style",
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 10], showticklabels=False,
                               gridcolor="rgba(201,168,76,0.12)"),
                angularaxis=dict(gridcolor="rgba(201,168,76,0.12)"),
            ),
            **_PLOTLY_LAYOUT,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_info:
        morpho = user_profile.get("morpho", "A")
        teint = user_profile.get("teint", "")
        morpho_data = advisor.get_morpho_summary(morpho)
        teint_data = advisor.get_teint_summary(teint)

        st.markdown(f"""
        <div class="fa-card">
            <span style="color:var(--accent);font-weight:600;">
                Morphologie {morpho} — {morpho_data.get('label', '')}
            </span><br>
            <span style="color:var(--text);font-size:0.88rem;">
                {morpho_data.get('tip', '')}
            </span>
        </div>
        """, unsafe_allow_html=True)

        if teint_data:
            colors_str = ", ".join(teint_data.get("colors", []))
            st.markdown(f"""
            <div class="fa-card" style="border-left:3px solid var(--blush);">
                <span style="color:var(--accent);font-weight:600;">Teint : {teint}</span><br>
                <span style="color:var(--text);font-size:0.88rem;">Palette : {colors_str}</span><br>
                <span style="color:var(--muted);font-size:0.8rem;">{teint_data.get('tip', '')}</span>
            </div>
            """, unsafe_allow_html=True)

        # Recent searches
        if search_hist:
            st.markdown("##### Dernieres recherches")
            for q in reversed(search_hist[-5:]):
                st.markdown(
                    f"<span style='color:var(--text);font-size:0.85rem;'>• {q}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Aucune recherche effectuee dans cette session.")
