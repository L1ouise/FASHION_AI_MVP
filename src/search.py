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


# ─── Search helper: persist results in session state ─────────────────────────
def _run_search(client, vec):
    """Execute vector search and store results in session state."""
    try:
        res = client.query_points(
            collection_name="fashion_images",
            query=vec,
            limit=8,
        ).points
        st.session_state.search_results = [
            {"id": str(p.id), "score": p.score, "payload": p.payload}
            for p in res
        ]
    except Exception as e:
        st.session_state.search_results = []
        st.error(f"Erreur de connexion a la base vectorielle : {e}")


def show_search(model, client, username=""):

    st.markdown("## Recherche")
    st.markdown("""
    <div class="fa-card">
        <span style="color:var(--text);font-size:0.9rem;">
            Trouvez des vetements par texte, image ou categorie.
            Les resultats sont classes par similarite visuelle.
        </span>
    </div>
    """, unsafe_allow_html=True)

    tab_text, tab_img, tab_cat = st.tabs(["Par texte", "Par image", "Par categorie"])

    # ─── TEXT SEARCH ──────────────────────────────────────────────────────
    with tab_text:
        st.markdown("##### Decrivez le vetement recherche")
        q = st.text_input(
            "Description",
            placeholder="ex : veste en cuir noir, robe rouge longue...",
            label_visibility="collapsed",
        )
        if st.button("Rechercher", key="search_text", use_container_width=True):
            if q:
                st.session_state.setdefault("search_history", []).append(q)
                with st.spinner("Recherche en cours..."):
                    _run_search(client, model.encode(q).tolist())
            else:
                st.warning("Veuillez entrer une description.")

    # ─── IMAGE SEARCH ────────────────────────────────────────────────────
    with tab_img:
        st.markdown("##### Importez une photo de vetement")
        st.caption("L'IA trouvera les articles les plus similaires du catalogue.")
        uploaded_file = st.file_uploader(
            "Choisir une image",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
        )
        if uploaded_file:
            c_prev, c_btn = st.columns([1, 2])
            with c_prev:
                img = Image.open(uploaded_file)
                # Resize for faster CLIP encoding (internal input is 224x224)
                if max(img.size) > 512:
                    ratio = 512 / max(img.size)
                    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
                st.image(img, width=180, caption="Image importee")
            with c_btn:
                if st.button("Lancer la recherche", key="search_img", use_container_width=True):
                    with st.spinner("Analyse de l'image..."):
                        _run_search(client, model.encode(img).tolist())

    # ─── CATEGORY SEARCH ─────────────────────────────────────────────────
    with tab_cat:
        st.markdown("##### Explorez par categorie")
        st.caption("Selectionnez un style pour voir les articles correspondants.")
        cat_cols = st.columns(4, gap="small")
        for i, (cat, keywords) in enumerate(CATEGORIES.items()):
            with cat_cols[i % 4]:
                if st.button(cat, key=f"cat_{cat}", use_container_width=True):
                    with st.spinner(f"Recherche {cat}..."):
                        _run_search(client, model.encode(keywords).tolist())

    # ─── RESULTS (persisted across reruns so buttons work) ────────────────
    results = st.session_state.get("search_results")

    if results is None:
        st.markdown("""
        <div class="fa-card" style="text-align:center;padding:2.5rem 1rem;">
            <span style="color:var(--muted);font-size:0.92rem;">
                Lancez une recherche pour decouvrir le catalogue
            </span>
        </div>
        """, unsafe_allow_html=True)
        return

    if not results:
        st.info("Aucun resultat trouve. Essayez une autre recherche.")
        return

    st.divider()
    st.markdown(f"#### Resultats ({len(results)} articles)")

    n_cols = min(len(results), 4)
    cols = st.columns(n_cols, gap="small")
    for i, item in enumerate(results):
        with cols[i % n_cols]:
            display_image(item["payload"], use_container_width=True)

            score_pct = round(item["score"] * 100)
            fname = item["payload"].get("filename", "")
            st.markdown(
                f"<span style='color:var(--accent);font-weight:600;'>{score_pct}%</span>"
                f"<span style='color:var(--muted);font-size:0.75rem;margin-left:6px;'>{fname}</span>",
                unsafe_allow_html=True,
            )

            if username:
                point_id = item["id"]
                is_fav = point_id in st.session_state.get("favorites", set())
                bc1, bc2 = st.columns(2)
                with bc1:
                    fav_label = "Retirer" if is_fav else "Sauvegarder"
                    if st.button(fav_label, key=f"fav_s_{point_id}", use_container_width=True):
                        toggle_favorite(client, username, point_id)
                        if is_fav:
                            st.session_state.favorites.discard(point_id)
                        else:
                            st.session_state.favorites.add(point_id)
                        st.rerun()
                with bc2:
                    if st.button("Essayer", key=f"vton_s_{point_id}", use_container_width=True):
                        st.session_state.vton_item = item["payload"]
                        st.session_state.page = "vton"
                        st.rerun()