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


def render(client, model, user_profile, username):
    """Render the Analytics page."""
    advisor = get_style_advisor()

    st.markdown("## Analyse du Catalogue")

    with st.spinner("Chargement des donnees..."):
        try:
            pts = client.scroll(collection_name="fashion_images", with_vectors=True)[0]
        except Exception:
            pts = []
            st.error("Erreur de connexion a la base vectorielle.")

    if not pts:
        st.info("Le catalogue est vide. Lancez le pipeline pour indexer des images.")
        return

    # ─── Key metrics row ─────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    m1.metric("Articles", len(pts))
    m2.metric("Favoris", len(st.session_state.get("favorites", set())))
    profile_fields = ["nom", "prenom", "age", "taille", "teint", "morpho"]
    has_img = bool(user_profile.get("profile_img_b64") or user_profile.get("profile_img_path"))
    pct = int(
        (sum(1 for f in profile_fields if user_profile.get(f)) + (1 if has_img else 0))
        / (len(profile_fields) + 1)
        * 100
    )
    m3.metric("Profil", f"{pct}%")

    st.divider()

    # ─── PCA scatter with clusters ───────────────────────────────────────
    vecs = [p.vector for p in pts]
    n_clusters = min(5, len(pts))
    pca = PCA(n_components=2).fit_transform(vecs)
    clusters = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit_predict(vecs)
    df = pd.DataFrame(pca, columns=["x", "y"])
    df["cluster"] = [f"Groupe {c + 1}" for c in clusters]

    fig_scatter = px.scatter(
        df,
        x="x",
        y="y",
        color="cluster",
        title="Distribution du catalogue (PCA + Clusters)",
        color_discrete_sequence=_COLOR_SEQ,
    )
    fig_scatter.update_layout(**_PLOTLY_LAYOUT)
    fig_scatter.update_layout(
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False),
        legend_title_text="",
    )
    fig_scatter.update_traces(marker=dict(size=8, opacity=0.7))
    st.plotly_chart(fig_scatter, use_container_width=True)

    # ─── Style profile radar chart ───────────────────────────────────────
    st.divider()
    st.markdown("### Votre profil style")

    # Derive radar axes from user profile and search history
    morpho = user_profile.get("morpho", "A")
    morpho_data = advisor.get_morpho_summary(morpho)

    # Compute simple style axis scores (0-10 scale)
    search_hist = st.session_state.get("search_history", [])
    hist_text = " ".join(search_hist).lower()

    def _score(keywords):
        return min(10, sum(1 for kw in keywords if kw in hist_text) * 3 + 3)

    radar_axes = {
        "Casual": _score(["casual", "jean", "t-shirt", "sneaker", "denim"]),
        "Formel": _score(["formal", "blazer", "costume", "cravate", "office"]),
        "Colore": _score(["rouge", "rose", "color", "vif", "jaune", "bright"]),
        "Minimal": _score(["noir", "blanc", "simple", "minimal", "basic"]),
        "Sportif": _score(["sport", "running", "athletic", "sneaker", "trainer"]),
        "Elegant": _score(["elegant", "soiree", "chic", "satin", "silk"]),
    }

    fig_radar = go.Figure()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=list(radar_axes.values()),
            theta=list(radar_axes.keys()),
            fill="toself",
            fillcolor="rgba(201,168,76,0.2)",
            line=dict(color="#c9a84c", width=2),
            name="Votre style",
        )
    )
    fig_radar.update_layout(
        title="Profil de style",
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 10], showticklabels=False, gridcolor="rgba(201,168,76,0.15)"),
            angularaxis=dict(gridcolor="rgba(201,168,76,0.15)"),
        ),
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # ─── Morpho + teint summary ──────────────────────────────────────────
    st.divider()
    teint = user_profile.get("teint", "")
    teint_data = advisor.get_teint_summary(teint)

    st.markdown(f"""
    <div class="fa-card">
        <span style="color:var(--accent);font-weight:600;">Morphologie {morpho} — {morpho_data.get('label', '')}</span><br>
        <span style="color:var(--text);font-size:0.9rem;">{morpho_data.get('tip', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    if teint_data:
        colors_str = ", ".join(teint_data.get("colors", []))
        st.markdown(f"""
        <div class="fa-card" style="border-left:3px solid var(--blush);">
            <span style="color:var(--accent);font-weight:600;">Teint : {teint}</span><br>
            <span style="color:var(--text);font-size:0.9rem;">Palette : {colors_str}</span><br>
            <span style="color:var(--muted);font-size:0.8rem;">{teint_data.get('tip', '')}</span>
        </div>
        """, unsafe_allow_html=True)

    # ─── Search history ──────────────────────────────────────────────────
    if search_hist:
        st.divider()
        st.markdown("### Historique de recherche (session)")
        for i, q in enumerate(reversed(search_hist[-10:]), 1):
            st.markdown(f"**{i}.** {q}")
