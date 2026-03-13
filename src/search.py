# search.py  —  Unified search page (Text / Image / Category)
import streamlit as st
from PIL import Image
from utile import display_image, toggle_favorite

# Category keywords for CLIP-based search
CATEGORIES = {
    "Casual":    "casual relaxed everyday denim cotton t-shirt jeans",
    "Formel":    "formal blazer suit professional office dress shirt",
    "Soiree":    "evening cocktail elegant satin sequin party dress",
    "Sport":     "athletic sporty sneakers activewear leggings",
    "Ete":       "summer light linen shorts sandals floral",
    "Hiver":     "winter coat warm wool sweater puffer jacket",
    "Boheme":    "bohemian boho flowy printed maxi skirt fringe",
    "Streetwear":"streetwear urban hoodie oversized sneakers graphic",
}


def show_search(model, client, username=""):

    st.markdown("### Recherche")
    st.caption("Trouvez des vetements par texte, image ou categorie.")

    tab_text, tab_img, tab_cat = st.tabs(["Par texte", "Par image", "Par categorie"])

    vec = None

    # ─── TEXT SEARCH ──────────────────────────────────────────────────────
    with tab_text:
        q = st.text_input(
            "Decrivez le vetement recherche",
            placeholder="ex: veste en cuir noir",
        )
        if st.button("Rechercher", key="search_text"):
            if q:
                if "search_history" not in st.session_state:
                    st.session_state.search_history = []
                st.session_state.search_history.append(q)
                with st.spinner("Recherche en cours..."):
                    vec = model.encode(q).tolist()
            else:
                st.warning("Veuillez entrer une description.")

    # ─── IMAGE SEARCH ────────────────────────────────────────────────────
    with tab_img:
        uploaded_file = st.file_uploader(
            "Importer une image",
            type=["jpg", "jpeg", "png"],
        )
        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, width=200)
            if st.button("Rechercher", key="search_img"):
                with st.spinner("Analyse de l'image..."):
                    vec = model.encode(img).tolist()

    # ─── CATEGORY SEARCH ─────────────────────────────────────────────────
    with tab_cat:
        st.caption("Selectionnez une categorie pour explorer le catalogue.")
        cols = st.columns(4)
        for i, (cat, keywords) in enumerate(CATEGORIES.items()):
            with cols[i % 4]:
                if st.button(cat, key=f"cat_{cat}", use_container_width=True):
                    with st.spinner(f"Recherche {cat}..."):
                        vec = model.encode(keywords).tolist()

    # ─── RESULTS ─────────────────────────────────────────────────────────
    if vec:
        try:
            res = client.query_points(
                collection_name="fashion_images",
                query=vec,
                limit=8,
            ).points
        except Exception:
            res = []
            st.error("Connexion impossible a la base vectorielle.")

        if res:
            st.markdown("#### Resultats")
            cols = st.columns(min(len(res), 4))
            for i, h in enumerate(res):
                with cols[i % 4]:
                    display_image(h.payload, use_container_width=True)
                    st.caption(f"Score : {round(h.score * 100)}%")

                    if username:
                        point_id = str(h.id)
                        is_fav = point_id in st.session_state.get("favorites", set())
                        fav_label = "Retirer" if is_fav else "Sauvegarder"
                        if st.button(fav_label, key=f"fav_s_{point_id}"):
                            toggle_favorite(client, username, point_id)
                            if is_fav:
                                st.session_state.favorites.discard(point_id)
                            else:
                                st.session_state.favorites.add(point_id)
                            st.rerun()

                        if st.button("Essayer", key=f"vton_s_{point_id}"):
                            st.session_state.vton_item = h.payload
                            st.session_state.page = "vton"
                            st.rerun()
        else:
            st.info("Aucun resultat trouve.")