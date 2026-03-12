# search.py  —  Unified 3-tab search page (Text / Category / Image)
import streamlit as st

from utile import display_image, toggle_favorite
from style_advisor import get_style_advisor


CATEGORY_CHIPS = [
    ("Tops", "casual top blouse shirt t-shirt"),
    ("Bottoms", "trousers pants jeans shorts skirt"),
    ("Dresses", "dress robe gown maxi midi"),
    ("Outerwear", "jacket coat blazer vest parka"),
    ("Shoes", "shoes sneakers heels boots sandals"),
    ("Accessories", "bag hat scarf belt jewelry watch"),
]


def _render_results(results, user_profile, username, client, prefix="sr"):
    """Render search results in a 2-column grid with advice and actions."""
    advisor = get_style_advisor()
    cols = st.columns(2)
    for i, hit in enumerate(results):
        with cols[i % 2]:
            display_image(hit.payload, use_container_width=True)

            # Style advice chip
            advice = advisor.get_advice(hit.payload, user_profile)
            st.markdown(
                f'<div style="font-size:0.78rem;color:var(--muted);padding:4px 0 8px;">{advice}</div>',
                unsafe_allow_html=True,
            )

            # Action buttons row
            point_id = str(hit.id)
            is_fav = point_id in st.session_state.get("favorites", set())

            c1, c2 = st.columns(2)
            with c1:
                fav_label = "Retirer" if is_fav else "Sauvegarder"
                if st.button(fav_label, key=f"fav_{prefix}_{point_id}"):
                    toggle_favorite(client, username, point_id)
                    if is_fav:
                        st.session_state.favorites.discard(point_id)
                    else:
                        st.session_state.favorites.add(point_id)
                    st.rerun()
            with c2:
                if st.button("Essayer", key=f"vton_{prefix}_{point_id}"):
                    st.session_state.vton_item = hit.payload
                    st.session_state.page = "vton"
                    st.rerun()


def render(client, model, user_profile, username):
    """Render the 3-tab search page."""
    st.markdown("## Recherche")

    tab_text, tab_cat, tab_img = st.tabs(["Texte", "Categorie", "Image"])

    # ─── Tab 1: Text Search ──────────────────────────────────────────────
    with tab_text:
        q = st.text_input(
            "Decrivez ce que vous cherchez",
            placeholder="Ex : robe rouge elegante, veste en cuir noire...",
            label_visibility="collapsed",
        )
        if q:
            # Track search history
            if "search_history" not in st.session_state:
                st.session_state.search_history = []
            st.session_state.search_history.append(q)

            with st.spinner("Recherche en cours..."):
                vec = model().encode(q).tolist()
                try:
                    res = client.search(collection_name="fashion_images", query_vector=vec, limit=8)
                except Exception:
                    res = []
                    st.error("Erreur de connexion a la base vectorielle.")

            if res:
                st.caption(f"{len(res)} resultats pour \u00ab {q} \u00bb")
                _render_results(res, user_profile, username, client, prefix="txt")
            else:
                st.info("Aucun resultat. Essayez d'autres mots-cles.")
        else:
            st.caption("Saisissez un mot-cle pour lancer la recherche semantique.")

    # ─── Tab 2: Category Search ──────────────────────────────────────────
    with tab_cat:
        cols = st.columns(3)
        selected_cat = None
        for i, (label, _keywords) in enumerate(CATEGORY_CHIPS):
            if cols[i % 3].button(label, key=f"cat_chip_{label}", use_container_width=True):
                selected_cat = label

        if selected_cat:
            keywords = dict(CATEGORY_CHIPS).get(selected_cat, selected_cat)
            with st.spinner(f"Recherche : {selected_cat}..."):
                vec = model().encode(keywords).tolist()
                try:
                    res = client.search(collection_name="fashion_images", query_vector=vec, limit=8)
                except Exception:
                    res = []
                    st.error("Erreur de connexion a la base vectorielle.")

            if res:
                st.caption(f"{len(res)} resultats pour {selected_cat}")
                _render_results(res, user_profile, username, client, prefix="cat")
            else:
                st.info(f"Aucun resultat pour {selected_cat}.")

    # ─── Tab 3: Image Search ────────────────────────────────────────────
    with tab_img:
        uploaded = st.file_uploader(
            "Importez une photo pour trouver des articles similaires",
            type=["png", "jpg", "jpeg"],
        )
        if uploaded:
            st.image(uploaded, width=200)
            with st.spinner("Analyse de l'image..."):
                vec = model().encode(uploaded).tolist()
                try:
                    res = client.search(collection_name="fashion_images", query_vector=vec, limit=8)
                except Exception:
                    res = []
                    st.error("Erreur de connexion a la base vectorielle.")

            if res:
                st.caption(f"{len(res)} articles similaires")
                _render_results(res, user_profile, username, client, prefix="img")
            else:
                st.info("Aucun resultat similaire.")
        else:
            st.caption("Importez une image de vetement ou de tenue pour rechercher par similarite visuelle.")
