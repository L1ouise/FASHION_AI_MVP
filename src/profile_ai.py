# profile_ai.py  —  Full-page profile editor
import streamlit as st
from utile import save_profile_to_qdrant, hash_password, get_user_profile, username_exists
from style_advisor import get_style_advisor


def show_signup_form(client, model):
    """Standalone signup form used on the login page."""
    with st.form("signup_form"):
        col1, col2 = st.columns(2)
        nom_input = col1.text_input("Nom", placeholder="Dupont")
        prenom_input = col2.text_input("Prenom", placeholder="Marie")

        col3, col4 = st.columns(2)
        age_input = col3.number_input("Age", min_value=15, max_value=100, value=25)
        taille_input = col4.number_input("Taille (cm)", min_value=120, max_value=220, value=170)

        teint_options = ["Clair / Pâle", "Intermédiaire / Mat", "Foncé / Noir"]
        teint_input = st.radio("Teint", teint_options, index=0, horizontal=True)

        morpho_options = ["A", "V", "H", "X", "O"]
        morpho_input = st.selectbox("Morphologie", morpho_options, index=0)

        username_input = st.text_input("Pseudo", placeholder="Votre identifiant unique")

        password_input = st.text_input("Mot de passe", type="password")
        password_confirm = st.text_input("Confirmer mot de passe", type="password")

        profile_img_input = st.file_uploader("Photo de profil (optionnel)", type=["png", "jpg", "jpeg"])

        submit_btn = st.form_submit_button("Creer mon compte")

        if submit_btn:
            if not username_input or not password_input:
                st.warning("Pseudo et mot de passe requis.")
                return
            if password_input != password_confirm:
                st.warning("Les mots de passe ne correspondent pas.")
                return
            if username_exists(client, username_input):
                st.error("Ce pseudo est deja pris.")
                return

            user_data = {
                "nom": nom_input,
                "prenom": prenom_input,
                "age": age_input,
                "taille": taille_input,
                "teint": teint_input,
                "morpho": morpho_input,
                "user_pseudo": username_input,
                "password": hash_password(password_input),
            }
            if profile_img_input is not None:
                user_data["profile_img_file"] = profile_img_input

            save_profile_to_qdrant(client, model, username_input, user_data)
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.session_state.page = "home"
            st.rerun()


def render(client, model, user_profile, username):
    """Full-page profile editor (post-login)."""
    advisor = get_style_advisor()
    if user_profile is None:
        user_profile = get_user_profile(client, username) or {}

    st.markdown("## Mon Profil")

    # ─── Identity section ────────────────────────────────────────────────
    st.markdown("""
    <div class="fa-card">
        <span style="color:var(--accent);font-weight:600;">Identite</span>
    </div>
    """, unsafe_allow_html=True)

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        nom_input = col1.text_input("Nom", value=user_profile.get("nom", ""), placeholder="Dupont")
        prenom_input = col2.text_input("Prenom", value=user_profile.get("prenom", ""), placeholder="Marie")

        # Username (read-only display)
        st.text_input("Pseudo", value=username, disabled=True)

        # ─── Body section ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Mensurations**")

        col3, col4 = st.columns(2)
        age_input = col3.number_input("Age", min_value=15, max_value=100, value=user_profile.get("age", 25))
        taille_input = col4.number_input("Taille (cm)", min_value=120, max_value=220, value=user_profile.get("taille", 170))

        teint_options = ["Clair / Pâle", "Intermédiaire / Mat", "Foncé / Noir"]
        default_teint = user_profile.get("teint", "Clair / Pâle")
        teint_idx = teint_options.index(default_teint) if default_teint in teint_options else 0
        teint_input = st.radio("Teint", teint_options, index=teint_idx, horizontal=True)

        # ─── Style preferences ───────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Style**")

        morpho_options = ["A", "V", "H", "X", "O"]
        morpho_labels = {
            "A": "A — Poire",
            "V": "V — Triangle inverse",
            "H": "H — Rectangulaire",
            "X": "X — Sablier",
            "O": "O — Ronde",
        }
        default_morpho = user_profile.get("morpho", "A")
        morpho_idx = morpho_options.index(default_morpho) if default_morpho in morpho_options else 0
        morpho_input = st.selectbox(
            "Morphologie",
            morpho_options,
            index=morpho_idx,
            format_func=lambda x: morpho_labels.get(x, x),
        )

        # ─── Password change ─────────────────────────────────────────────
        st.markdown("---")
        modify_password = st.checkbox("Modifier le mot de passe")
        password_to_store = None
        if modify_password:
            pw = st.text_input("Nouveau mot de passe", type="password")
            pw_confirm = st.text_input("Confirmer le mot de passe", type="password")
            if pw and pw_confirm and pw != pw_confirm:
                st.warning("Les mots de passe ne correspondent pas.")
            elif pw:
                password_to_store = hash_password(pw)

        # ─── Profile image ───────────────────────────────────────────────
        st.markdown("---")
        profile_img_input = st.file_uploader("Photo de profil", type=["png", "jpg", "jpeg"])

        submit_btn = st.form_submit_button("Enregistrer les modifications")

        if submit_btn:
            updated = {}
            if nom_input != user_profile.get("nom", ""):
                updated["nom"] = nom_input
            if prenom_input != user_profile.get("prenom", ""):
                updated["prenom"] = prenom_input
            if age_input != user_profile.get("age", 25):
                updated["age"] = age_input
            if taille_input != user_profile.get("taille", 170):
                updated["taille"] = taille_input
            if teint_input != user_profile.get("teint", "Clair / Pâle"):
                updated["teint"] = teint_input
            if morpho_input != user_profile.get("morpho", "A"):
                updated["morpho"] = morpho_input
            if password_to_store:
                updated["password"] = password_to_store
            if profile_img_input is not None:
                updated["profile_img_file"] = profile_img_input

            if updated:
                save_profile_to_qdrant(client, model, username, updated)
                st.success("Profil mis a jour.")
                st.rerun()
            else:
                st.info("Aucune modification detectee.")

    # ─── Style advisor preview ───────────────────────────────────────────
    st.divider()
    st.markdown("### Recommandations personnalisees")

    morpho_data = advisor.get_morpho_summary(user_profile.get("morpho", "A"))
    teint_data = advisor.get_teint_summary(user_profile.get("teint", ""))

    if morpho_data:
        rec = ", ".join(morpho_data.get("recommended", []))
        avoid = ", ".join(morpho_data.get("avoid", []))
        st.markdown(f"""
        <div class="fa-card">
            <span style="color:var(--accent);font-weight:600;">Morphologie {user_profile.get('morpho', 'A')} — {morpho_data.get('label', '')}</span><br>
            <span style="color:var(--text);font-size:0.9rem;">A privilegier : {rec}</span><br>
            <span style="color:var(--blush);font-size:0.9rem;">A eviter : {avoid}</span><br>
            <span style="color:var(--muted);font-size:0.85rem;">{morpho_data.get('tip', '')}</span>
        </div>
        """, unsafe_allow_html=True)

    if teint_data:
        colors_str = ", ".join(teint_data.get("colors", []))
        st.markdown(f"""
        <div class="fa-card" style="border-left:3px solid var(--blush);">
            <span style="color:var(--accent);font-weight:600;">Palette couleurs</span><br>
            <span style="color:var(--text);font-size:0.9rem;">{colors_str}</span><br>
            <span style="color:var(--muted);font-size:0.85rem;">{teint_data.get('tip', '')}</span>
        </div>
        """, unsafe_allow_html=True)