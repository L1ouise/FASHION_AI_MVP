# auth.py — Landing page + Authentication
import streamlit as st
from utile import get_user_profile, verify_password
from profile_ai import show_signup_form


# ─── SVG icons for landing features ──────────────────────────────────────────
_FEATURE_ICONS = {
    "search": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c9a84c" stroke-width="1.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
    "looks": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c9a84c" stroke-width="1.5" stroke-linecap="round"><path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"/></svg>',
    "vton": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c9a84c" stroke-width="1.5" stroke-linecap="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "ai": '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c9a84c" stroke-width="1.5" stroke-linecap="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>',
}


def render_landing_page():
    """Professional landing page shown before authentication."""
    st.markdown("""
    <div style="text-align:center;padding:4rem 1rem 2rem;">
        <div style="margin-bottom:0.5rem;">
            <span style="font-family:'Playfair Display',serif;font-size:3.5rem;color:#c9a84c;font-weight:700;letter-spacing:2px;">Fashion AI</span>
        </div>
        <p style="color:#8e8e9e;font-size:1.15rem;max-width:500px;margin:0 auto 0.5rem;">
            Votre assistant mode intelligent propulse par l'IA
        </p>
        <p style="color:#6a6a7a;font-size:0.9rem;max-width:420px;margin:0 auto;">
            Recherchez, composez et essayez des tenues adaptees a votre morphologie et votre style
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ─── Feature cards ───────────────────────────────────────────────────
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    features = [
        ("search", "Recherche intelligente", "Trouvez des vetements par texte, image ou categorie"),
        ("looks", "Generation de looks", "Tenues personnalisees selon votre morphologie"),
        ("vton", "Essayage virtuel", "Visualisez les vetements sur votre silhouette"),
        ("ai", "Conseils IA", "Recommandations basees sur votre profil style"),
    ]
    cols = st.columns(4)
    for i, (ic, title, desc) in enumerate(features):
        with cols[i]:
            st.markdown(f"""
            <div style="background:#16213e;border-radius:12px;padding:1.5rem 1rem;text-align:center;
                        border:1px solid rgba(201,168,76,0.1);min-height:160px;">
                <div style="margin-bottom:0.8rem;">{_FEATURE_ICONS[ic]}</div>
                <p style="color:#c9a84c;font-weight:600;font-size:0.95rem;margin:0 0 6px;">{title}</p>
                <p style="color:#8e8e9e;font-size:0.78rem;margin:0;line-height:1.4;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    # ─── CTA buttons ─────────────────────────────────────────────────────
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    _, c1, c2, _ = st.columns([1.5, 1, 1, 1.5])
    with c1:
        if st.button("Se connecter", key="land_login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
    with c2:
        if st.button("Creer un compte", key="land_signup", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()

    st.markdown("""
    <div style="text-align:center;padding:3rem 0 1rem;">
        <p style="color:#4a4a5a;font-size:0.75rem;">Fashion AI &mdash; Intelligence artificielle au service du style</p>
    </div>
    """, unsafe_allow_html=True)


def render_auth_page(client, model, view="login"):
    """Render login or signup form with back navigation."""
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Retour", key="auth_back"):
            st.session_state.page = "landing"
            st.rerun()

    st.markdown("""
    <div style="text-align:center;margin:1rem 0 2rem;">
        <span style="font-family:'Playfair Display',serif;font-size:2rem;color:#c9a84c;font-weight:700;">Fashion AI</span>
    </div>
    """, unsafe_allow_html=True)

    if view == "login":
        _render_login_form(client)
    else:
        _render_signup_form(client, model)


def _render_login_form(client):
    """Login form."""
    st.markdown("#### Connexion")
    with st.form("login_form"):
        username_input = st.text_input("Pseudo", placeholder="Votre identifiant")
        password_input = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
        login_submitted = st.form_submit_button("Se connecter", use_container_width=True)

    if login_submitted:
        if not username_input or not password_input:
            st.warning("Veuillez remplir tous les champs.")
        else:
            user_profile = get_user_profile(client, username_input)
            if user_profile and "password" in user_profile:
                if verify_password(password_input, user_profile["password"]):
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
            else:
                st.error("Utilisateur non trouve.")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    if st.button("Pas encore de compte ? Creer un compte", key="switch_signup"):
        st.session_state.page = "signup"
        st.rerun()


def _render_signup_form(client, model):
    """Signup form."""
    st.markdown("#### Creer un compte")
    show_signup_form(client, model)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    if st.button("Deja un compte ? Se connecter", key="switch_login"):
        st.session_state.page = "login"
        st.rerun()
