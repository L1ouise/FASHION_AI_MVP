# app.py
import streamlit as st
import requests
import os
from datetime import datetime
from utile import init_tools, get_user_profile, hash_password
from profile_ai import show_profile_sidebar

# ─── Airflow config ───────────────────────────────────────────────────────────
AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
DAG_ID = "fashion_pipeline"

# ---------------- PAGE CONFIG (must be first st call) ----------------
st.set_page_config(
    page_title="Fashion AI",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------- MOBILE-FRIENDLY CSS ----------------
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    /* ─── Global mobile adjustments ─── */
    .block-container {
        padding: 1rem 1rem !important;
        max-width: 100% !important;
    }
    /* Larger touch targets */
    .stButton > button {
        width: 100%;
        min-height: 48px;
        font-size: 1rem;
        border-radius: 12px;
    }
    .stFormSubmitButton > button {
        width: 100%;
        min-height: 48px;
        font-size: 1rem;
        border-radius: 12px;
    }
    /* Responsive text inputs */
    .stTextInput > div > div > input {
        font-size: 1rem;
        min-height: 44px;
    }
    /* Tabs: bigger touch targets */
    .stTabs [data-baseweb="tab"] {
        min-height: 48px;
        font-size: 1rem;
        padding: 0.5rem 1rem;
    }
    /* Selectbox */
    .stSelectbox > div > div {
        min-height: 44px;
    }
    /* Sidebar profile image */
    [data-testid="stSidebar"] img {
        border-radius: 50%;
        max-width: 120px;
        margin: 0 auto;
        display: block;
    }
    /* Image grids: responsive cards */
    [data-testid="stImage"] {
        border-radius: 12px;
        overflow: hidden;
    }
    /* Mobile: stack columns on small screens */
    @media (max-width: 640px) {
        .block-container {
            padding: 0.5rem 0.5rem !important;
        }
        [data-testid="column"] {
            width: 50% !important;
            flex: 0 0 50% !important;
            min-width: 0 !important;
        }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.25rem !important; }
        h3 { font-size: 1.1rem !important; }
        /* Hide hamburger menu label on mobile */
        header [data-testid="stToolbar"] {
            display: none;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------------- INIT ----------------
model, client = init_tools()

# ---------------- SESSION ----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
 
# ---------------- LOGIN / SIGNUP ----------------
if not st.session_state.logged_in:
 
    st.title("🔐 Fashion AI - Accès")
    tab1, tab2 = st.tabs(["Connexion", "Inscription"])
 
    # -------- LOGIN --------
    with tab1:
        with st.form("login_form"):
            username_input = st.text_input("Nom d'utilisateur")
            password_input = st.text_input("Mot de passe", type="password")
            login_submitted = st.form_submit_button("Se connecter")
 
        if login_submitted:
            user_profile = get_user_profile(client, username_input)
 
            if user_profile and 'password' in user_profile:
                if hash_password(password_input) == user_profile['password']:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    st.success(f"Connexion réussie ! Bienvenue {username_input}")
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect")
            else:
                st.error("Utilisateur non trouvé")
 
        # Bouton mot de passe/pseudo oublié
        if st.button("Mot de passe ou pseudo oublié ?"):
            st.info("Contactez l'administrateur pour réinitialiser votre compte.")
 
    # -------- SIGNUP --------
    with tab2:
        st.subheader("Créer mon compte et mon profil")
        show_profile_sidebar(client, model, username="", user_profile=None, require_password=True)
 
# ---------------- DASHBOARD ----------------
else:
    username = st.session_state.username
    user_profile = get_user_profile(client, username)  # Toujours récupérer le profil complet
 
    st.sidebar.title(f"👋 Bonjour {username}")
 
    # -------- IMAGE PROFIL --------
    profile_img_path = user_profile.get("profile_img_path") or user_profile.get("profile_img_file")
    if profile_img_path:
        st.sidebar.image(profile_img_path, width=150)
 
    # -------- LOGOUT --------
    if st.sidebar.button("Déconnexion"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
 
    # -------- MODIFIER PROFIL --------
    with st.sidebar.expander("Modifier mon profil"):
        show_profile_sidebar(client, model, username, user_profile=user_profile, require_password=False)
 
    # ---------------- DASHBOARD ----------------
    mode = st.selectbox(
        "Fonctionnalité",
        ["Recherche", "Look Generator", "Analytics", "Pipeline Admin"]
    )
 
    # ---------------- RECHERCHE ----------------
    if mode == "Recherche":
        q = st.text_input("🔍 Recherche texte", placeholder="Ex: robe rouge, veste en cuir...")
        if q:
            vec = model.encode(q).tolist()
            res = client.search(collection_name="fashion_images", query_vector=vec, limit=4)
            cols = st.columns(2)  # 2 columns = mobile-friendly grid
            for i, h in enumerate(res):
                cols[i % 2].image(h.payload["path"], use_container_width=True)
 
    # ---------------- LOOK GENERATOR ----------------
    elif mode == "Look Generator":
        st.header("✨ Salon d'Essayage")
        from utile import get_color_advice
 
        teint = user_profile.get("teint", "Clair / Pâle")
        st.info(get_color_advice(teint))
 
        img = st.file_uploader("Uploader une pièce ou utiliser votre photo", type=["png", "jpg", "jpeg"])
        source_img = img if img else profile_img_path
 
        if source_img:
            vec = model.encode(source_img).tolist()
            res = client.search(collection_name="fashion_images", query_vector=vec, limit=5)
            st.image(res[0].payload["path"], width=200, use_container_width=True)
            st.write("Suggestions assorties :")
            cols = st.columns(2)  # 2 columns for mobile
            for i, h in enumerate(res[1:]):
                cols[i % 2].image(h.payload["path"], use_container_width=True)
 
    # ---------------- ANALYTICS ----------------
    elif mode == "Analytics":
        st.header("📊 Analyse Style")
        import pandas as pd
        import plotly.express as px
        from sklearn.decomposition import PCA
 
        pts = client.scroll(collection_name="fashion_images", with_vectors=True)[0]
        vecs = [p.vector for p in pts]
        pca = PCA(n_components=2).fit_transform(vecs)
        df = pd.DataFrame(pca, columns=["x", "y"])
        fig = px.scatter(df, x="x", y="y", title="Distribution du catalogue")
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- PIPELINE ADMIN ----------------
    elif mode == "Pipeline Admin":
        st.header("⚙️ Gestion du Pipeline Airflow")

        col1, col2 = st.columns(2)

        # Trigger DAG manually
        with col1:
            if st.button("▶️ Lancer le pipeline maintenant"):
                run_id = f"manual__{datetime.utcnow().isoformat()}"
                try:
                    response = requests.post(
                        f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns",
                        json={"dag_run_id": run_id},
                        auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                        timeout=10,
                    )
                    if response.status_code == 200:
                        st.success(f"Pipeline lancé ! Run ID: {run_id}")
                    else:
                        st.error(f"Erreur : {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Impossible de contacter Airflow. Vérifiez que le service est démarré.")

        # Get last DAG run status
        with col2:
            if st.button("🔄 Statut du dernier run"):
                try:
                    response = requests.get(
                        f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns"
                        "?limit=1&order_by=-execution_date",
                        auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                        timeout=10,
                    )
                    if response.status_code == 200:
                        runs = response.json().get("dag_runs", [])
                        if runs:
                            last = runs[0]
                            st.json({
                                "state": last["state"],
                                "run_id": last["dag_run_id"],
                                "start_date": last["start_date"],
                                "end_date": last["end_date"],
                            })
                        else:
                            st.info("Aucun run trouvé.")
                    else:
                        st.error(f"Erreur : {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Impossible de contacter Airflow. Vérifiez que le service est démarré.")

        # Run history
        st.subheader("📋 Historique des runs")
        try:
            response = requests.get(
                f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns"
                "?limit=5&order_by=-execution_date",
                auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
                timeout=10,
            )
            if response.status_code == 200:
                runs = response.json().get("dag_runs", [])
                if runs:
                    for run in runs:
                        color = (
                            "🟢" if run["state"] == "success"
                            else "🔴" if run["state"] == "failed"
                            else "🟡"
                        )
                        st.write(
                            f"{color} `{run['dag_run_id']}` — "
                            f"{run['state']} — {run['start_date']}"
                        )
                else:
                    st.info("Aucun run dans l'historique.")
        except requests.exceptions.ConnectionError:
            st.warning("Airflow non disponible — historique indisponible.")