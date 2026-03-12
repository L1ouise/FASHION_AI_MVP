# app.py  —  Fashion AI · Luxury mobile-first entrypoint
import streamlit as st
import requests
from datetime import datetime

from utile import (
    _get_secret,
    init_tools,
    get_user_profile,
    get_favorites,
    toggle_favorite,
    display_image,
)


# ─── Airflow config (graceful if unreachable) ────────────────────────────────
AIRFLOW_BASE_URL = _get_secret("AIRFLOW_BASE_URL", "")
AIRFLOW_USER = _get_secret("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = _get_secret("AIRFLOW_PASSWORD", "admin")
DAG_ID = "fashion_pipeline"


# ─── Page config (must be first st.* call) ───────────────────────────────────
st.set_page_config(
    page_title="Fashion AI",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM — Dark luxury CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

:root {
  --bg:       #1a1a2e;
  --surface:  #16213e;
  --card:     #0f3460;
  --accent:   #c9a84c;
  --blush:    #e8c4b8;
  --text:     #f5f0e8;
  --muted:    #9a9080;
  --radius:   12px;
  --shadow:   0 4px 24px rgba(0,0,0,0.4);
}

html, body, [data-testid="stAppViewContainer"] {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 { font-family: 'Playfair Display', serif; color: var(--accent); }

/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { display: none !important; }

/* Mobile-first container */
.block-container {
  padding: 0 16px 80px 16px !important;
  max-width: 480px !important;
  margin: 0 auto !important;
}

/* Cards */
.fa-card {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: var(--shadow);
  border: 1px solid rgba(201,168,76,0.15);
}

/* Buttons */
.stButton > button {
  background: var(--accent) !important;
  color: var(--bg) !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 500 !important;
  padding: 12px 24px !important;
  width: 100% !important;
  min-height: 44px !important;
  transition: transform 0.1s;
}
.stButton > button:active { transform: scale(0.97); }

.stFormSubmitButton > button {
  background: var(--accent) !important;
  color: var(--bg) !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  min-height: 44px !important;
  width: 100% !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
  font-size: 1rem;
  min-height: 44px;
  border-radius: 10px;
  background: var(--surface) !important;
  color: var(--text) !important;
  border-color: rgba(201,168,76,0.3) !important;
}
.stSelectbox > div > div { min-height: 44px; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 0; justify-content: center; }
.stTabs [data-baseweb="tab"] {
  min-height: 44px; font-size: 0.95rem; font-weight: 500;
  padding: 0.5rem 1.5rem; border-radius: var(--radius) var(--radius) 0 0;
  color: var(--muted); font-family: 'DM Sans', sans-serif;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--accent); }

/* Image cards */
[data-testid="stImage"] {
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: transform 0.2s;
}
[data-testid="stImage"]:hover { transform: translateY(-2px); }

/* Metrics */
[data-testid="stMetricValue"] { color: var(--accent) !important; font-family: 'Playfair Display', serif; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; }

/* Sticky header */
.fa-header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 999;
  background: rgba(26,26,46,0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(201,168,76,0.2);
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; height: 56px;
}
.fa-logo { font-family:'Playfair Display',serif; font-size:22px; color:#c9a84c; font-weight:700; }
.fa-nav-icons { display:flex; gap:16px; }
.fa-nav-icons svg { width:22px; height:22px; stroke:#f5f0e8; cursor:pointer; }
/* Push content below fixed header */
[data-testid="stAppViewContainer"] > div:first-child { padding-top: 64px !important; }

/* Feature cards (home page) */
.feature-card {
  background: var(--surface);
  border: 1px solid rgba(201,168,76,0.15);
  border-radius: var(--radius);
  padding: 1.2rem;
  text-align: center;
  transition: transform 0.2s, box-shadow 0.2s;
  min-height: 120px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 24px rgba(201,168,76,0.15);
}
.feature-card .label { font-weight: 600; font-size: 1rem; color: var(--accent); font-family: 'Playfair Display', serif; }
.feature-card .desc { font-size: 0.8rem; color: var(--muted); margin-top: 0.3rem; }

/* Welcome banner */
.welcome-banner {
  background: linear-gradient(135deg, var(--surface) 0%, var(--card) 100%);
  border: 1px solid rgba(201,168,76,0.2);
  padding: 1.2rem 1.5rem;
  border-radius: var(--radius);
  margin-bottom: 16px;
}
.welcome-banner h2 { margin: 0; font-size: 1.2rem; color: var(--accent); }
.welcome-banner p  { margin: 0.2rem 0 0 0; color: var(--muted); font-size: 0.9rem; }

/* Mobile tweaks */
@media (max-width: 640px) {
  .block-container { padding: 0 10px 80px 10px !important; }
  [data-testid="column"] { width: 50% !important; flex: 0 0 50% !important; min-width: 0 !important; }
  h1 { font-size: 1.5rem !important; }
  h2 { font-size: 1.2rem !important; }
  .feature-card { min-height: 100px; padding: 0.8rem; }
}
</style>
""", unsafe_allow_html=True)


# ─── Init ─────────────────────────────────────────────────────────────────────
model, client = init_tools()


# ─── Session state ────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "page" not in st.session_state:
    st.session_state.page = "home"
if "favorites" not in st.session_state:
    st.session_state.favorites = set()
if "search_history" not in st.session_state:
    st.session_state.search_history = []


def go_to(page):
    st.session_state.page = page


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH GATE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    from auth import render_login_page
    render_login_page(client, model)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP (logged in)
# ══════════════════════════════════════════════════════════════════════════════
else:
    username = st.session_state.username
    user_profile = get_user_profile(client, username) or {}
    prenom = user_profile.get("prenom", username)

    # Load favorites into session
    if not st.session_state.favorites:
        st.session_state.favorites = set(get_favorites(client, username))

    # ─── Sticky header HTML ──────────────────────────────────────────────
    st.markdown("""
    <div class="fa-header">
      <span class="fa-logo">FA</span>
      <span style="font-family:'Playfair Display',serif;font-size:16px;color:#f5f0e8;">Fashion AI</span>
      <div class="fa-nav-icons">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Functional navigation bar (st.buttons under the header) ─────────
    nav_cols = st.columns(7)
    nav_items = [
        ("Accueil", "home"),
        ("Recherche", "search"),
        ("Looks", "looks"),
        ("Essayage", "vton"),
        ("Favoris", "favorites"),
        ("Stats", "analytics"),
        ("Profil", "profile"),
    ]
    for i, (label, page_key) in enumerate(nav_items):
        if nav_cols[i].button(label, key=f"nav_{page_key}", use_container_width=True):
            go_to(page_key)
            st.rerun()

    # Pipeline and logout in a slim row
    aux_cols = st.columns([1, 1, 2])
    if aux_cols[0].button("Pipeline", key="nav_pipeline", use_container_width=True):
        go_to("pipeline")
        st.rerun()
    if aux_cols[1].button("Deconnexion", key="nav_logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.page = "home"
        st.session_state.favorites = set()
        st.rerun()

    st.markdown("---")

    page = st.session_state.page

    # ══════════════════════════════════════════════════════════════════════════
    #  HOME
    # ══════════════════════════════════════════════════════════════════════════
    if page == "home":
        st.markdown(f"""
        <div class="welcome-banner">
            <h2>Bonjour, {prenom}</h2>
            <p>Que souhaitez-vous faire aujourd'hui ?</p>
        </div>
        """, unsafe_allow_html=True)

        # Profile completeness
        profile_fields = ["nom", "prenom", "age", "taille", "teint", "morpho"]
        has_img = bool(user_profile.get("profile_img_b64"))
        filled = sum(1 for f in profile_fields if user_profile.get(f)) + (1 if has_img else 0)
        pct = int(filled / (len(profile_fields) + 1) * 100)
        if pct < 100:
            st.progress(pct / 100, text=f"Profil complete a {pct}%")
            st.caption("Completez votre profil pour de meilleures recommandations.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div class="feature-card">
                <div class="label">Recherche</div>
                <div class="desc">Trouvez des pieces par texte, categorie ou image</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Ouvrir", key="home_search"):
                go_to("search")
                st.rerun()
        with c2:
            st.markdown("""
            <div class="feature-card">
                <div class="label">Look Generator</div>
                <div class="desc">Creez des tenues assorties a votre morphologie</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Creer un look", key="home_looks"):
                go_to("looks")
                st.rerun()

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("""
            <div class="feature-card">
                <div class="label">Essayage Virtuel</div>
                <div class="desc">Visualisez les vetements sur un mannequin</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Essayer", key="home_vton"):
                go_to("vton")
                st.rerun()
        with c4:
            st.markdown("""
            <div class="feature-card">
                <div class="label">Analytics</div>
                <div class="desc">Analysez votre style et le catalogue</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Statistiques", key="home_analytics"):
                go_to("analytics")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    #  SEARCH (delegated to module)
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "search":
        from search import render as search_render
        search_render(client, model, user_profile, username)

    # ══════════════════════════════════════════════════════════════════════════
    #  LOOK GENERATOR (delegated to module)
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "looks":
        from look_generator import render as looks_render
        looks_render(client, model, user_profile, username)

    # ══════════════════════════════════════════════════════════════════════════
    #  VIRTUAL TRY-ON (delegated to module)
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "vton":
        from vton import render as vton_render
        vton_render(client, model, user_profile, username)

    # ══════════════════════════════════════════════════════════════════════════
    #  FAVORITES (inline — simple)
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "favorites":
        st.markdown("## Mes Favoris")
        fav_ids = list(st.session_state.favorites)
        if fav_ids:
            try:
                fav_points = client.retrieve(collection_name="fashion_images", ids=fav_ids)
            except Exception:
                fav_points = []

            if fav_points:
                st.caption(f"{len(fav_points)} article(s) sauvegarde(s)")
                cols = st.columns(2)
                for i, pt in enumerate(fav_points):
                    with cols[i % 2]:
                        display_image(pt.payload, use_container_width=True)
                        if st.button("Retirer", key=f"unfav_{pt.id}"):
                            toggle_favorite(client, username, str(pt.id))
                            st.session_state.favorites.discard(str(pt.id))
                            st.rerun()
            else:
                st.info("Vos favoris n'ont pas pu etre charges.")
        else:
            st.info("Vous n'avez pas encore de favoris. Explorez le catalogue et sauvegardez des pieces.")

    # ══════════════════════════════════════════════════════════════════════════
    #  ANALYTICS (delegated to module)
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "analytics":
        from analytic import render as analytics_render
        analytics_render(client, model, user_profile, username)

    # ══════════════════════════════════════════════════════════════════════════
    #  PROFILE (delegated to module)
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "profile":
        from profile_ai import render as profile_render
        profile_render(client, model, user_profile, username)

    # ══════════════════════════════════════════════════════════════════════════
    #  PIPELINE ADMIN (inline, graceful Airflow fallback)
    # ══════════════════════════════════════════════════════════════════════════
    elif page == "pipeline":
        st.markdown("## Pipeline Airflow")

        if not AIRFLOW_BASE_URL:
            st.info("Pipeline orchestration non configuree — AIRFLOW_BASE_URL absent des secrets.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                if st.button("Lancer le pipeline", use_container_width=True):
                    run_id = f"manual__{datetime.utcnow().isoformat()}"
                    try:
                        response = requests.post(
                            f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns",
                            json={"dag_run_id": run_id},
                            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                            timeout=3,
                        )
                        if response.status_code == 200:
                            st.success("Pipeline lance avec succes.")
                        else:
                            st.error(f"Erreur : {response.text}")
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                        st.warning("Pipeline orchestration non disponible — Airflow est hors ligne.")

            with col2:
                if st.button("Rafraichir le statut", use_container_width=True):
                    try:
                        response = requests.get(
                            f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns"
                            "?limit=1&order_by=-execution_date",
                            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                            timeout=3,
                        )
                        if response.status_code == 200:
                            runs = response.json().get("dag_runs", [])
                            if runs:
                                last = runs[0]
                                state = last["state"]
                                color = "var(--accent)" if state == "success" else "var(--blush)"
                                st.markdown(
                                    f'<div class="fa-card">Dernier run : <span style="color:{color};font-weight:600;">{state}</span></div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.info("Aucun run trouve.")
                        else:
                            st.error(f"Erreur : {response.text}")
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                        st.warning("Pipeline orchestration non disponible — Airflow est hors ligne.")

            st.markdown("---")
            st.markdown("**Historique recent**")

            try:
                response = requests.get(
                    f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns"
                    "?limit=5&order_by=-execution_date",
                    auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                    timeout=3,
                )
                if response.status_code == 200:
                    runs = response.json().get("dag_runs", [])
                    if runs:
                        for run in runs:
                            state = run["state"]
                            rid = run["dag_run_id"]
                            date = run["start_date"] or "—"
                            st.markdown(f"**{state}** — {rid} — {date}")
                    else:
                        st.caption("Aucun run dans l'historique.")
                else:
                    st.caption("Impossible de charger l'historique.")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                st.warning("Pipeline orchestration non disponible — Airflow est hors ligne.")
