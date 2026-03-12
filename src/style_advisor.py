# style_advisor.py
import streamlit as st


@st.cache_resource
def get_style_advisor():
    """Singleton StyleAdvisor — cached across sessions."""
    return StyleAdvisor()


class StyleAdvisor:
    """Personalised fashion advice engine combining morphology rules and skin-tone palettes."""

    MORPHO_RULES = {
        "X": {
            "label": "Sablier",
            "recommended": ["wrap dresses", "fitted cuts", "belted waist", "pencil skirts"],
            "avoid": ["boxy tops", "oversized silhouettes"],
            "tip": "Mettez en valeur votre taille marquee avec des coupes ajustees.",
        },
        "H": {
            "label": "Rectangulaire",
            "recommended": ["peplum tops", "ruffles", "layering", "flared skirts"],
            "avoid": ["straight-cut dresses", "column silhouettes"],
            "tip": "Creez des courbes visuelles avec du volume strategique.",
        },
        "A": {
            "label": "Poire",
            "recommended": ["A-line skirts", "boat neck", "structured shoulders", "flared tops"],
            "avoid": ["wide-leg trousers", "hip pockets", "tight bottoms"],
            "tip": "Equilibrez la silhouette en structurant le haut du corps.",
        },
        "V": {
            "label": "Triangle inverse",
            "recommended": ["flared trousers", "A-line dresses", "pleated skirts", "V-neck"],
            "avoid": ["padded shoulders", "boat neck", "horizontal stripes on top"],
            "tip": "Apportez du volume au bas pour harmoniser la silhouette.",
        },
        "O": {
            "label": "Ronde",
            "recommended": ["V-neck", "empire waist", "monochrome outfits", "vertical lines"],
            "avoid": ["horizontal stripes", "clingy fabrics", "tight belts"],
            "tip": "Privilegiez les lignes verticales et les coupes fluides.",
        },
    }

    TEINT_PALETTE = {
        "Clair / Pâle": {
            "colors": ["navy", "emerald", "blush pink", "burgundy"],
            "tip": "Les tons froids et profonds subliment votre teint clair.",
        },
        "Intermédiaire / Mat": {
            "colors": ["terracotta", "olive", "deep red", "camel"],
            "tip": "Les tons chauds et terreux mettent en valeur votre teint mat.",
        },
        "Foncé / Noir": {
            "colors": ["bright yellow", "white", "cobalt", "violet"],
            "tip": "Les couleurs vives et contrastees illuminent votre teint fonce.",
        },
    }

    OCCASION_KEYWORDS = {
        "Casual": "casual relaxed everyday comfortable cotton denim",
        "Work": "professional office formal blazer structured clean",
        "Evening": "elegant evening gown cocktail sequin satin",
        "Sport": "athletic sporty activewear sneakers comfortable stretch",
        "Weekend": "relaxed weekend brunch comfortable chic linen",
    }

    def get_advice(self, item_payload: dict, user_profile: dict) -> str:
        """Return a human-readable style tip for a specific item + user combination."""
        morpho = user_profile.get("morpho", "")
        teint = user_profile.get("teint", "")
        tips = []

        if morpho in self.MORPHO_RULES:
            rules = self.MORPHO_RULES[morpho]
            # Check item tags / description against recommended / avoid lists
            item_desc = " ".join(str(v) for v in item_payload.values() if isinstance(v, str)).lower()
            matched_good = [r for r in rules["recommended"] if any(w in item_desc for w in r.lower().split())]
            matched_bad = [a for a in rules["avoid"] if any(w in item_desc for w in a.lower().split())]

            if matched_good:
                tips.append(f"Ideal pour morphologie {morpho} : {', '.join(matched_good)}")
            if matched_bad:
                tips.append(f"Attention morphologie {morpho} : evitez {', '.join(matched_bad)}")
            if not matched_good and not matched_bad:
                tips.append(rules["tip"])

        if teint in self.TEINT_PALETTE:
            palette = self.TEINT_PALETTE[teint]
            tips.append(f"Palette recommandee : {', '.join(palette['colors'])}")

        return " · ".join(tips) if tips else "Article compatible avec votre profil."

    def get_morpho_summary(self, morpho: str) -> dict:
        """Return full morphology info dict."""
        return self.MORPHO_RULES.get(morpho, {})

    def get_teint_summary(self, teint: str) -> dict:
        """Return full skin-tone info dict."""
        return self.TEINT_PALETTE.get(teint, {})

    def build_occasion_query(self, occasion: str, user_profile: dict) -> str:
        """Build a composite text query for CLIP encoding."""
        morpho = user_profile.get("morpho", "")
        teint = user_profile.get("teint", "")
        base_keywords = self.OCCASION_KEYWORDS.get(occasion, occasion.lower())
        morpho_label = self.MORPHO_RULES.get(morpho, {}).get("label", "")
        parts = [f"{occasion} outfit"]
        if morpho_label:
            parts.append(f"for {morpho_label} body shape")
        if teint:
            parts.append(f"{teint} skin tone")
        parts.append(base_keywords)
        return " ".join(parts)
