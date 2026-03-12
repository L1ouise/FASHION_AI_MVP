# look_generator.py  —  Morphology-aware outfit builder
import streamlit as st

from utile import display_image, toggle_favorite
from style_advisor import get_style_advisor

OCCASIONS = ["Casual", "Work", "Evening", "Sport", "Weekend"]


def render(client, model, user_profile, username):
    """Render the Look Generator page."""
    advisor = get_style_advisor()
    morpho = user_profile.get("morpho", "A")
    teint = user_profile.get("teint", "")
    taille = user_profile.get("taille", "")

    st.markdown("## Generateur de Looks")

    # ─── Profile summary card ────────────────────────────────────────────
    morpho_data = advisor.get_morpho_summary(morpho)
    teint_data = advisor.get_teint_summary(teint)

    profile_parts = [f"Morphologie <strong>{morpho}</strong> ({morpho_data.get('label', '')})"]
    if teint:
        profile_parts.append(f"Teint : <strong>{teint}</strong>")
    if taille:
        profile_parts.append(f"Taille : <strong>{taille} cm</strong>")

    st.markdown(f"""
    <div class="fa-card">
        <span style="color:var(--accent);font-weight:600;">Votre profil style</span><br>
        <span style="color:var(--text);">{'  ·  '.join(profile_parts)}</span>
    </div>
    """, unsafe_allow_html=True)

    # Morpho tip
    if morpho_data.get("tip"):
        st.markdown(f"""
        <div class="fa-card" style="border-left:3px solid var(--accent);">
            <span style="color:var(--text);font-size:0.9rem;">{morpho_data['tip']}</span>
        </div>
        """, unsafe_allow_html=True)

    # Color palette recommendation
    if teint_data.get("colors"):
        colors_str = ", ".join(teint_data["colors"])
        st.markdown(f"""
        <div class="fa-card" style="border-left:3px solid var(--blush);">
            <span style="color:var(--accent);font-weight:600;">Palette recommandee</span><br>
            <span style="color:var(--text);font-size:0.9rem;">{colors_str}</span><br>
            <span style="color:var(--muted);font-size:0.8rem;">{teint_data.get('tip', '')}</span>
        </div>
        """, unsafe_allow_html=True)

    # ─── Occasion selector ───────────────────────────────────────────────
    st.markdown("### Occasion")
    occ_cols = st.columns(len(OCCASIONS))
    selected_occasion = None
    for i, occ in enumerate(OCCASIONS):
        if occ_cols[i].button(occ, key=f"occ_{occ}", use_container_width=True):
            selected_occasion = occ

    # Remember last selection
    if selected_occasion:
        st.session_state.look_occasion = selected_occasion
    occasion = st.session_state.get("look_occasion")

    if not occasion:
        st.caption("Selectionnez une occasion pour generer un look personnalise.")
        return

    # ─── Generate outfit ─────────────────────────────────────────────────
    query = advisor.build_occasion_query(occasion, user_profile)

    with st.spinner(f"Creation du look {occasion}..."):
        vec = model().encode(query).tolist()
        try:
            results = client.search(collection_name="fashion_images", query_vector=vec, limit=6)
        except Exception:
            results = []
            st.error("Erreur de connexion a la base vectorielle.")

    if not results:
        st.info("Aucun article trouve. Le catalogue est peut-etre vide.")
        return

    st.markdown(f"### Look {occasion}")

    # Stack display: top → bottom → shoes → accessory
    SLOT_LABELS = ["Piece principale", "Haut", "Bas", "Chaussures", "Accessoire 1", "Accessoire 2"]
    look_ids = []

    for i, hit in enumerate(results):
        label = SLOT_LABELS[i] if i < len(SLOT_LABELS) else f"Article {i+1}"
        point_id = str(hit.id)
        look_ids.append(point_id)

        st.markdown(f"**{label}**")
        c1, c2 = st.columns([1, 2])
        with c1:
            display_image(hit.payload, use_container_width=True)
        with c2:
            advice = advisor.get_advice(hit.payload, user_profile)
            st.markdown(
                f'<div style="font-size:0.85rem;color:var(--text);padding:4px 0;">{advice}</div>',
                unsafe_allow_html=True,
            )
            bc1, bc2 = st.columns(2)
            with bc1:
                is_fav = point_id in st.session_state.get("favorites", set())
                fav_label = "Retirer" if is_fav else "Sauvegarder"
                if st.button(fav_label, key=f"fav_look_{point_id}"):
                    toggle_favorite(client, username, point_id)
                    if is_fav:
                        st.session_state.favorites.discard(point_id)
                    else:
                        st.session_state.favorites.add(point_id)
                    st.rerun()
            with bc2:
                if st.button("Essayer", key=f"vton_look_{point_id}"):
                    st.session_state.vton_item = hit.payload
                    st.session_state.page = "vton"
                    st.rerun()

    # ─── Save look ───────────────────────────────────────────────────────
    st.divider()
    if st.button("Sauvegarder ce look", use_container_width=True):
        from utile import generate_user_id
        user_id = generate_user_id(username)
        profile = user_profile or {}
        saved_looks = profile.get("saved_looks", [])
        saved_looks.append({"occasion": occasion, "items": look_ids})
        try:
            client.set_payload(
                collection_name="user_profiles",
                payload={"saved_looks": saved_looks},
                points=[user_id],
            )
            st.success("Look sauvegarde dans votre profil.")
        except Exception:
            st.error("Erreur lors de la sauvegarde.")
