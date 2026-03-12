# vton.py  —  Virtual Try-On page
import io
import streamlit as st
from PIL import Image

from style_advisor import get_style_advisor

# ─── Mannequin metadata (keyed by morpho) ────────────────────────────────────
# In production, place actual PNGs in src/assets/mannequins/
# Each entry maps to a silhouette image file.
MANNEQUIN_MAP = {
    "X": {"file": "mannequin_x.png", "label": "Sablier", "overlay_pos": (60, 120), "scale": 0.55},
    "H": {"file": "mannequin_h.png", "label": "Rectangulaire", "overlay_pos": (55, 130), "scale": 0.55},
    "A": {"file": "mannequin_a.png", "label": "Poire", "overlay_pos": (50, 125), "scale": 0.55},
    "V": {"file": "mannequin_v.png", "label": "Triangle inverse", "overlay_pos": (55, 115), "scale": 0.55},
    "O": {"file": "mannequin_o.png", "label": "Ronde", "overlay_pos": (50, 130), "scale": 0.55},
}

# Default mannequin if morpho not set
DEFAULT_MORPHO = "X"


def _try_remove_background(image_bytes: bytes) -> Image.Image:
    """Remove background using rembg (CPU). Falls back to raw image if unavailable."""
    try:
        from rembg import remove
        output = remove(image_bytes)
        return Image.open(io.BytesIO(output)).convert("RGBA")
    except ImportError:
        st.warning("Module rembg non installe — fond non supprime.")
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        st.warning(f"Erreur suppression du fond : {e}")
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")


def _compose_vton(mannequin: Image.Image, clothing: Image.Image, position: tuple, scale: float) -> Image.Image:
    """Overlay clothing PNG (transparent bg) onto mannequin."""
    mannequin = mannequin.convert("RGBA")
    w = int(mannequin.width * scale)
    h = int(clothing.height * (w / clothing.width))
    clothing_resized = clothing.resize((w, h), Image.LANCZOS)
    result = mannequin.copy()
    result.paste(clothing_resized, position, clothing_resized)
    return result.convert("RGB")


def _generate_placeholder_mannequin(morpho: str) -> Image.Image:
    """Generate a simple placeholder mannequin silhouette when asset files are missing."""
    img = Image.new("RGBA", (300, 500), (22, 33, 62, 255))  # surface color
    # Draw a simple silhouette shape (just a filled oval as placeholder)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Head
    draw.ellipse([125, 20, 175, 70], fill=(201, 168, 76, 180))
    # Body proportions vary by morpho
    shapes = {
        "X": [(100, 80, 200, 160), (120, 160, 180, 280), (95, 280, 205, 450)],
        "H": [(105, 80, 195, 160), (105, 160, 195, 280), (105, 280, 195, 450)],
        "A": [(115, 80, 185, 160), (110, 160, 190, 280), (85, 280, 215, 450)],
        "V": [(90, 80, 210, 160), (105, 160, 195, 280), (110, 280, 190, 450)],
        "O": [(95, 80, 205, 160), (90, 160, 210, 280), (100, 280, 200, 450)],
    }
    for rect in shapes.get(morpho, shapes["X"]):
        draw.rounded_rectangle(rect, radius=15, fill=(201, 168, 76, 80))
    return img


def _load_mannequin(morpho: str) -> Image.Image:
    """Load mannequin image from assets or generate placeholder."""
    import os
    info = MANNEQUIN_MAP.get(morpho, MANNEQUIN_MAP[DEFAULT_MORPHO])
    # Try loading from assets folder (relative to this file)
    assets_dir = os.path.join(os.path.dirname(__file__), "assets", "mannequins")
    filepath = os.path.join(assets_dir, info["file"])
    if os.path.exists(filepath):
        return Image.open(filepath).convert("RGBA")
    return _generate_placeholder_mannequin(morpho)


def render(client, model, user_profile, username):
    """Render the Virtual Try-On page."""
    advisor = get_style_advisor()
    morpho = user_profile.get("morpho", DEFAULT_MORPHO)
    teint = user_profile.get("teint", "")
    info = MANNEQUIN_MAP.get(morpho, MANNEQUIN_MAP[DEFAULT_MORPHO])

    st.markdown("## Essayage Virtuel")

    # ─── Profile summary card ────────────────────────────────────────────
    morpho_data = advisor.get_morpho_summary(morpho)
    st.markdown(f"""
    <div class="fa-card">
        <span style="color:var(--accent);font-weight:600;">Votre silhouette</span><br>
        <span style="color:var(--text);">Morphologie <strong>{morpho}</strong> ({morpho_data.get('label', '')})</span>
        {f' · Teint : <strong>{teint}</strong>' if teint else ''}
    </div>
    """, unsafe_allow_html=True)

    # ─── Step 1: Mannequin display ───────────────────────────────────────
    mannequin_img = _load_mannequin(morpho)
    st.image(mannequin_img.convert("RGB"), caption=f"Mannequin {info['label']}", width=200)

    # ─── Step 2: Clothing selection ──────────────────────────────────────
    st.markdown("### Selectionnez un vetement")
    clothing_source = None

    # Option A: from session state (passed from search / look generator)
    vton_item = st.session_state.get("vton_item")
    if vton_item:
        st.info("Article pre-selectionne depuis la recherche.")
        # vton_item is expected to be a Qdrant point payload with image data
        b64 = vton_item.get("thumb_b64")
        if b64:
            import base64
            clothing_source = base64.b64decode(b64)
        st.session_state.pop("vton_item", None)

    # Option B: upload directly
    uploaded = st.file_uploader("Ou importez une image de vetement", type=["png", "jpg", "jpeg"])
    if uploaded:
        clothing_source = uploaded.read()

    if clothing_source:
        with st.spinner("Traitement de l'image..."):
            clothing_rgba = _try_remove_background(clothing_source)

        st.image(clothing_rgba.convert("RGB"), caption="Vetement (fond supprime)", width=200)

        # ─── Step 3: Compose ─────────────────────────────────────────────
        with st.spinner("Composition de l'essayage..."):
            result = _compose_vton(
                mannequin_img,
                clothing_rgba,
                position=info["overlay_pos"],
                scale=info["scale"],
            )

        st.markdown("### Resultat")
        st.image(result, use_container_width=True)

        # Download button
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=90)
        st.download_button(
            "Telecharger le look",
            data=buf.getvalue(),
            file_name="mon_look_vton.jpg",
            mime="image/jpeg",
        )

        # Style advice
        advice = advisor.get_advice({"description": "clothing item"}, user_profile)
        st.markdown(f"""
        <div class="fa-card" style="border-left:3px solid var(--accent);">
            <span style="color:var(--accent);font-weight:600;">Conseil Style</span><br>
            <span style="color:var(--text);font-size:0.9rem;">{advice}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="fa-card">
            <span style="color:var(--muted);">
                Importez une image de vetement ou selectionnez un article depuis la recherche
                pour lancer l'essayage virtuel.
            </span>
        </div>
        """, unsafe_allow_html=True)
