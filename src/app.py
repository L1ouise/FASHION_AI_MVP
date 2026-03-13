# app.py — Fashion AI · Professional Streamlit App
import streamlit as st

st.set_page_config(page_title="Fashion AI", page_icon="\u2726", layout="wide")

from utile import (
    init_tools,
    get_user_profile,
    get_favorites,
    display_image,
    toggle_favorite,
)
from auth import render_landing_page, render_auth_page
from profile_ai import show_profile_sidebar
from search import show_search
import look_generator
import vton
import analytic

# ─── SVG Icons (Lucide-style) ─────────────────────────────────────────────────
def _icon(name, size=22, color="#c9a84c"):
    _SVG = {
        "home": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "search": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
        "shirt": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"/></svg>',
        "user": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "heart": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>',
        "mirror": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "chart": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>',
        "logout": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>',
    }
    return _SVG.get(name, "")

# ─── Design System CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

:root {
    --surface: #1a1a2e;
    --surface-alt: #16213e;
    --surface-hover: #1e2a4a;
    --accent: #c9a84c;
    --accent-soft: rgba(201,168,76,0.12);
    --blush: #e8c4b8;
    --text: #f5f0e8;
    --muted: #8e8e9e;
    --dim: #5a5a6a;
    --radius: 12px;
    --radius-sm: 8px;
}

/* ─── Global ─────────────────────────────────────── */
.stApp { font-family: 'DM Sans', sans-serif; }
h1, h2, h3, h4 { font-family: 'Playfair Display', serif !important; }

/* ─── Sidebar ────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}
[data-testid="stSidebar"] * {
    color: var(--text) !important;
}
[data-testid="stSidebar"] button {
    text-align: left !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 0.55rem 0.9rem !important;
    margin-bottom: 1px !important;
    background: transparent !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    cursor: pointer !important;
    pointer-events: auto !important;
    transition: background 0.2s ease;
}
[data-testid="stSidebar"] button:hover {
    background: var(--accent-soft) !important;
}

/* ─── Cards ──────────────────────────────────────── */
.fa-card {
    background: var(--surface-alt);
    border-radius: var(--radius);
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
    border: 1px solid rgba(201,168,76,0.1);
}
.home-card {
    background: var(--surface-alt);
    border-radius: var(--radius);
    padding: 2rem 1.2rem;
    text-align: center;
    border: 1px solid rgba(201,168,76,0.08);
    transition: all 0.25s ease;
    cursor: pointer;
    min-height: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.home-card:hover {
    border-color: rgba(201,168,76,0.3);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.home-card .card-icon { margin-bottom: 1rem; }
.home-card .card-title {
    color: var(--accent);
    font-size: 1.15rem;
    font-weight: 600;
    margin: 0 0 6px;
    font-family: 'DM Sans', sans-serif;
}
.home-card .card-desc {
    color: var(--muted);
    font-size: 0.8rem;
    margin: 0;
    line-height: 1.4;
}

/* ─── Nav active state ───────────────────────────── */
.nav-active {
    background: var(--accent-soft) !important;
    border-left: 3px solid var(--accent) !important;
}

/* ─── Buttons ────────────────────────────────────── */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

/* ─── Metric cards ───────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--surface-alt);
    border-radius: var(--radius);
    padding: 1rem;
    border: 1px solid rgba(201,168,76,0.1);
}

/* ─── Tabs ───────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# ─── Init ─────────────────────────────────────────────────────────────────────
model, client = init_tools()

# ─── Session state defaults ───────────────────────────────────────────────────
_defaults = {
    "logged_in": False,
    "username": "",
    "page": "landing",
    "favorites": set(),
    "search_history": [],
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH GATE — Landing / Login / Signup
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    if st.session_state.page in ("login", "signup"):
        render_auth_page(client, model, st.session_state.page)
    else:
        render_landing_page()
    st.stop()

# Ensure logged-in user doesn't stay on auth pages
if st.session_state.page in ("landing", "login", "signup"):
    st.session_state.page = "home"

# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGED-IN  —  sidebar + page router
# ═══════════════════════════════════════════════════════════════════════════════
username = st.session_state.username
user_profile = get_user_profile(client, username) or {}

# Sync favorites from Qdrant → session state (once per login)
if "favorites_loaded" not in st.session_state:
    _fav_ids = get_favorites(client, username)
    st.session_state.favorites = set(str(f) for f in _fav_ids)
    st.session_state.favorites_loaded = True

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;margin:0 0 18px;">
        <span style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--accent);font-weight:700;">FA</span>
        <p style="margin:2px 0 0;font-size:0.85rem;color:var(--muted);">Fashion AI</p>
    </div>
    """, unsafe_allow_html=True)

    # Profile image
    b64 = user_profile.get("profile_img_b64")
    if b64:
        st.markdown(
            f'<div style="text-align:center;margin-bottom:8px;">'
            f'<img src="data:image/jpeg;base64,{b64}" '
            f'style="width:80px;height:80px;border-radius:50%;object-fit:cover;'
            f'border:2px solid var(--accent);"></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<p style="text-align:center;font-weight:600;margin-bottom:16px;">{username}</p>',
        unsafe_allow_html=True,
    )

    # Navigation
    pages = {
        "home":      ("Accueil",          "home"),
        "search":    ("Recherche",        "search"),
        "looks":     ("Looks",            "shirt"),
        "vton":      ("Essayage Virtuel", "mirror"),
        "favorites": ("Favoris",          "heart"),
        "analytics": ("Analytics",        "chart"),
        "profile":   ("Mon Profil",       "user"),
    }

    for key, (label, ic) in pages.items():
        if st.button(f"  {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.divider()
    if st.button("  Deconnexion", key="nav_logout", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ─── Page router ──────────────────────────────────────────────────────────────
page = st.session_state.page

# ── HOME ──────────────────────────────────────────────────────────────────────
if page == "home":
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1.5rem;">
        <span style="font-family:'Playfair Display',serif;font-size:2.6rem;color:var(--accent);font-weight:700;">Fashion AI</span>
        <p style="color:var(--muted);font-size:0.95rem;margin-top:6px;">Bienvenue — que souhaitez-vous faire ?</p>
    </div>
    """, unsafe_allow_html=True)

    # 4 clickable cards: Search, Looks, Profile, Favorites
    home_items = [
        ("search",    "search", "Recherche",  "Trouvez des vetements par texte, image ou categorie"),
        ("looks",     "shirt",  "Looks",      "Generez des tenues adaptees a votre profil"),
        ("profile",   "user",   "Mon Profil", "Consultez et editez vos preferences style"),
        ("favorites", "heart",  "Favoris",    "Retrouvez vos articles sauvegardes"),
    ]

    c1, c2 = st.columns(2)
    for idx, (pg, ic, title, desc) in enumerate(home_items):
        with (c1 if idx % 2 == 0 else c2):
            st.markdown(f"""
            <div class="home-card">
                <div class="card-icon">{_icon(ic, size=36, color="#c9a84c")}</div>
                <p class="card-title">{title}</p>
                <p class="card-desc">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Ouvrir {title}", key=f"home_{pg}", use_container_width=True):
                st.session_state.page = pg
                st.rerun()

# ── SEARCH ────────────────────────────────────────────────────────────────────
elif page == "search":
    show_search(model, client, username)

# ── LOOK GENERATOR ────────────────────────────────────────────────────────────
elif page == "looks":
    look_generator.render(client, model, user_profile, username)

# ── VTON ──────────────────────────────────────────────────────────────────────
elif page == "vton":
    vton.render(client, model, user_profile, username)

# ── FAVORITES ─────────────────────────────────────────────────────────────────
elif page == "favorites":
    st.markdown("## Mes Favoris")
    fav_ids = get_favorites(client, username)
    if not fav_ids:
        st.info("Aucun favori pour le moment. Explorez le catalogue et sauvegardez des articles.")
    else:
        try:
            safe_ids = []
            for fid in fav_ids:
                try:
                    safe_ids.append(int(fid))
                except (ValueError, TypeError):
                    safe_ids.append(str(fid))
            points = client.retrieve(
                collection_name="fashion_images",
                ids=safe_ids,
                with_payload=True,
            )
        except Exception as e:
            points = []
            st.error(f"Erreur lors du chargement des favoris : {e}")
        if points:
            cols = st.columns(min(len(points), 4))
            for i, pt in enumerate(points):
                with cols[i % 4]:
                    display_image(pt.payload, use_container_width=True)
                    name = pt.payload.get("filename", pt.payload.get("nom", ""))
                    if name:
                        st.caption(name)
                    point_id = str(pt.id)
                    if st.button("Retirer", key=f"unfav_{point_id}"):
                        toggle_favorite(client, username, point_id)
                        st.session_state.favorites.discard(point_id)
                        st.rerun()
        elif fav_ids:
            st.warning("Les articles favoris n'ont pas ete trouves dans le catalogue.")

# ── ANALYTICS ─────────────────────────────────────────────────────────────────
elif page == "analytics":
    analytic.render(client, model, user_profile, username)

# ── PROFILE ───────────────────────────────────────────────────────────────────
elif page == "profile":
    show_profile_sidebar(client, model, username, user_profile, require_password=False)