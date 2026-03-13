# vton.py  —  Virtual Try-On page (production rewrite)
"""
Virtual try-on with proper garment fitting:
 1. Background removal (rembg)
 2. Garment bounding-box crop (remove transparent margins)
 3. Normalised composition on a fixed internal canvas (600×900)
 4. Body-zone alignment per morphology (shoulders → hem)
 5. Responsive display via use_container_width
 6. Fully French UI
"""
from __future__ import annotations

import base64
import io
import os

import streamlit as st
from PIL import Image, ImageDraw

from style_advisor import get_style_advisor

# ─── Internal composition canvas (fixed, device-independent) ─────────────────
CANVAS_W, CANVAS_H = 600, 900
SURFACE_COLOR = (22, 33, 62, 255)       # --surface #1a1a2e
ACCENT_RGBA   = (201, 168, 76)          # --accent  #c9a84c

DEFAULT_MORPHO = "X"

# ─── Body-zone map per morphology ────────────────────────────────────────────
# All values are normalised ratios of the CANVAS (0.0 – 1.0).
#   shoulder_y : top of garment overlay (ratio from canvas top)
#   shoulder_w : garment width at shoulders (ratio of canvas width)
#   waist_w    : garment width at waist (used for shape hint only)
#   hip_w      : garment width at hips
#   hem_y      : max bottom of garment (ratio from canvas top)
MORPHO_ZONES = {
    "X": {
        "label": "Sablier",
        "shoulder_y": 0.18, "shoulder_w": 0.52,
        "waist_w": 0.38, "hip_w": 0.50,
        "hem_y": 0.92,
    },
    "H": {
        "label": "Rectangulaire",
        "shoulder_y": 0.19, "shoulder_w": 0.50,
        "waist_w": 0.48, "hip_w": 0.50,
        "hem_y": 0.92,
    },
    "A": {
        "label": "Poire",
        "shoulder_y": 0.18, "shoulder_w": 0.46,
        "waist_w": 0.44, "hip_w": 0.54,
        "hem_y": 0.92,
    },
    "V": {
        "label": "Triangle inverse",
        "shoulder_y": 0.17, "shoulder_w": 0.56,
        "waist_w": 0.44, "hip_w": 0.46,
        "hem_y": 0.92,
    },
    "O": {
        "label": "Ronde",
        "shoulder_y": 0.18, "shoulder_w": 0.54,
        "waist_w": 0.52, "hip_w": 0.54,
        "hem_y": 0.92,
    },
}

MANNEQUIN_FILES = {
    "X": "mannequin_x.png",
    "H": "mannequin_h.png",
    "A": "mannequin_a.png",
    "V": "mannequin_v.png",
    "O": "mannequin_o.png",
}


# ═════════════════════════════════════════════════════════════════════════════
#  Image helpers
# ═════════════════════════════════════════════════════════════════════════════

def _try_remove_background(image_bytes: bytes) -> Image.Image:
    """Remove background via rembg. Resizes large images first for speed."""
    # Pre-resize: rembg is very slow on large images
    MAX_DIM = 1024
    img = Image.open(io.BytesIO(image_bytes))
    if max(img.size) > MAX_DIM:
        ratio = MAX_DIM / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
    try:
        from rembg import remove
        output = remove(image_bytes)
        return Image.open(io.BytesIO(output)).convert("RGBA")
    except ImportError:
        st.warning("Module rembg non installe. Le fond n'a pas ete supprime.")
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        st.warning(f"Erreur suppression du fond : {e}")
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")


def _crop_to_content(img: Image.Image) -> Image.Image:
    """Crop an RGBA image to its non-transparent bounding box."""
    bbox = img.getbbox()          # (left, upper, right, lower) of non-zero alpha
    if bbox is None:
        return img
    return img.crop(bbox)


def _compose_vton(mannequin: Image.Image, garment: Image.Image, morpho: str) -> Image.Image:
    """
    Compose garment onto mannequin using body-zone alignment.

    Steps:
      1. Crop garment to its visible bounding box (remove transparent margins).
      2. Scale garment width to the morphology's shoulder width on the canvas.
      3. Cap garment height so it doesn't exceed hem_y.
      4. Centre horizontally on the mannequin.
      5. Place top edge at shoulder_y.
    """
    zones = MORPHO_ZONES.get(morpho, MORPHO_ZONES[DEFAULT_MORPHO])

    # Work on the internal canvas size
    mannequin = mannequin.convert("RGBA").resize((CANVAS_W, CANVAS_H), Image.LANCZOS)

    # 1. Crop garment to its visible pixels
    garment = _crop_to_content(garment.convert("RGBA"))
    if garment.width == 0 or garment.height == 0:
        return mannequin.convert("RGB")

    # 2. Target garment width = shoulder_w × canvas width
    target_w = int(zones["shoulder_w"] * CANVAS_W)
    scale = target_w / garment.width
    target_h = int(garment.height * scale)

    # 3. Cap height so garment doesn't exceed hem_y
    max_h = int((zones["hem_y"] - zones["shoulder_y"]) * CANVAS_H)
    if target_h > max_h:
        target_h = max_h
        scale = target_h / garment.height
        target_w = int(garment.width * scale)

    garment_resized = garment.resize((target_w, target_h), Image.LANCZOS)

    # 4. Position: centred horizontally, top at shoulder_y
    x = (CANVAS_W - target_w) // 2
    y = int(zones["shoulder_y"] * CANVAS_H)

    # 5. Composite
    result = mannequin.copy()
    result.paste(garment_resized, (x, y), garment_resized)
    return result.convert("RGB")


# ─── Mannequin loading / generation ──────────────────────────────────────────

def _generate_placeholder_mannequin(morpho: str) -> Image.Image:
    """Procedural mannequin silhouette on the internal canvas."""
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), SURFACE_COLOR)
    draw = ImageDraw.Draw(img)

    cx = CANVAS_W // 2

    # Head
    head_r = 30
    draw.ellipse(
        [cx - head_r, 40, cx + head_r, 40 + head_r * 2],
        fill=(*ACCENT_RGBA, 200),
    )
    # Neck
    draw.rectangle([cx - 8, 100, cx + 8, 130], fill=(*ACCENT_RGBA, 140))

    zones = MORPHO_ZONES.get(morpho, MORPHO_ZONES[DEFAULT_MORPHO])

    # Torso segments: shoulders → waist → hips → hem
    segments = [
        (0.15, zones["shoulder_w"]),   # top of torso
        (0.30, zones["shoulder_w"]),   # lower shoulders
        (0.45, zones["waist_w"]),      # waist
        (0.60, zones["hip_w"]),        # hips
        (0.90, zones["hip_w"] * 0.5),  # ankles
    ]

    prev_y = int(0.15 * CANVAS_H)
    prev_hw = int(zones["shoulder_w"] * CANVAS_W / 2)
    for ratio_y, ratio_w in segments[1:]:
        cur_y = int(ratio_y * CANVAS_H)
        cur_hw = int(ratio_w * CANVAS_W / 2)
        draw.polygon(
            [
                (cx - prev_hw, prev_y),
                (cx + prev_hw, prev_y),
                (cx + cur_hw, cur_y),
                (cx - cur_hw, cur_y),
            ],
            fill=(*ACCENT_RGBA, 70),
        )
        prev_y, prev_hw = cur_y, cur_hw

    return img


def _load_mannequin(morpho: str) -> Image.Image:
    """Load mannequin PNG from assets or generate a placeholder."""
    fname = MANNEQUIN_FILES.get(morpho, MANNEQUIN_FILES[DEFAULT_MORPHO])
    assets_dir = os.path.join(os.path.dirname(__file__), "assets", "mannequins")
    filepath = os.path.join(assets_dir, fname)
    if os.path.exists(filepath):
        return Image.open(filepath).convert("RGBA")
    return _generate_placeholder_mannequin(morpho)


# ═════════════════════════════════════════════════════════════════════════════
#  Main page render
# ═════════════════════════════════════════════════════════════════════════════

def render(client, model, user_profile, username):
    """Render the Virtual Try-On page — fully French UI."""
    advisor = get_style_advisor()
    morpho = user_profile.get("morpho", DEFAULT_MORPHO)
    teint = user_profile.get("teint", "")
    zones = MORPHO_ZONES.get(morpho, MORPHO_ZONES[DEFAULT_MORPHO])

    # ── Page title ────────────────────────────────────────────────────────
    st.markdown("## 👗 Essayage Virtuel")

    # ── Profile summary ──────────────────────────────────────────────────
    morpho_label = zones["label"]
    card_teint = f" · Teint : <strong>{teint}</strong>" if teint else ""
    st.markdown(f"""
    <div class="fa-card">
        <span style="color:var(--accent);font-weight:600;">Votre silhouette</span><br>
        <span style="color:var(--text);">
            Morphologie <strong>{morpho}</strong> ({morpho_label}){card_teint}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Étape 1 — Silhouette ─────────────────────────────────────────────
    st.markdown("#### 1. Votre mannequin")
    mannequin_img = _load_mannequin(morpho)
    # Show mannequin at a fixed preview width — responsive via container
    st.image(
        mannequin_img.convert("RGB"),
        caption=f"Silhouette {morpho_label}",
        width=220,
    )

    # ── Étape 2 — Import du vêtement ─────────────────────────────────────
    st.markdown("#### 2. Importez votre vêtement")

    clothing_source = None

    # Option A: pre-selected item from search / look generator
    vton_item = st.session_state.get("vton_item")
    if vton_item:
        st.success("✔ Article pré-sélectionné depuis la recherche.")
        b64 = vton_item.get("thumb_b64")
        if b64:
            clothing_source = base64.b64decode(b64)
        st.session_state.pop("vton_item", None)

    # Option B: direct upload
    uploaded = st.file_uploader(
        "Choisissez une image de vêtement",
        type=["png", "jpg", "jpeg"],
        help="Formats acceptés : PNG, JPG, JPEG",
    )
    if uploaded:
        clothing_source = uploaded.read()

    # ── Nothing selected yet ─────────────────────────────────────────────
    if not clothing_source:
        st.markdown("""
        <div class="fa-card">
            <span style="color:var(--muted);">
                Importez une image ou sélectionnez un article depuis la recherche
                pour lancer l'essayage.
            </span>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Étape 3 — Aperçu du vêtement importé ─────────────────────────────
    st.markdown("#### 3. Aperçu du vêtement")
    with st.spinner("Suppression du fond en cours…"):
        clothing_rgba = _try_remove_background(clothing_source)

    st.image(clothing_rgba.convert("RGB"), caption="Vêtement (fond supprimé)", width=200)

    # ── Étape 4 — Résultat de l'essayage ─────────────────────────────────
    st.markdown("#### 4. Résultat de l'essayage")
    with st.spinner("Composition en cours…"):
        result = _compose_vton(mannequin_img, clothing_rgba, morpho)

    # Responsive: use_container_width ensures the fixed 600×900 canvas
    # scales to any device width without distortion.
    st.image(result, use_container_width=True)

    # ── Étape 5 — Conseil style ──────────────────────────────────────────
    advice = advisor.get_advice({"description": "clothing item"}, user_profile)
    st.markdown(f"""
    <div class="fa-card" style="border-left:3px solid var(--accent);">
        <span style="color:var(--accent);font-weight:600;">💡 Conseil Style</span><br>
        <span style="color:var(--text);font-size:0.9rem;">{advice}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Étape 6 — Téléchargement ─────────────────────────────────────────
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=92)
    st.download_button(
        "📥 Télécharger le résultat",
        data=buf.getvalue(),
        file_name="essayage_virtuel.jpg",
        mime="image/jpeg",
        use_container_width=True,
    )
