# auth.py  —  Login / Signup forms (no emojis, professional)
import streamlit as st

from utile import get_user_profile, verify_password
from profile_ai import show_signup_form


def render_login_page(client, model):
    """Render the full authentication page with Login and Signup tabs."""

    st.markdown("""
    <div style="text-align:center;margin:32px 0 24px;">
        <span style="font-family:'Playfair Display',serif;font-size:2.4rem;color:var(--accent);font-weight:700;">FA</span>
        <h1 style="margin:4px 0 0;font-size:1.6rem;">Fashion AI</h1>
        <p style="color:var(--muted);font-size:0.95rem;">Votre assistant mode intelligent</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["Connexion", "Creer un compte"])

    with tab_login:
        with st.form("login_form"):
            username_input = st.text_input("Pseudo", placeholder="Entrez votre identifiant")
            password_input = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
            st.markdown("")  # spacer
            login_submitted = st.form_submit_button("Se connecter")

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

    with tab_signup:
        show_signup_form(client, model)
