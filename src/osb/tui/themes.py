"""Color themes for the OSB reader.

Built on Textual's theme system. Each theme supplies the app's full palette
via the Theme `variables` dict (so the custom `$bg`, `$surface`, `$text-verse`,
… used throughout the stylesheets resolve), plus the standard design tokens
(primary/background/surface/…) that built-in widgets style themselves with.

Themes are registered and the saved one applied in ``OrthodoxStudyApp.__init__``
— before the stylesheet is parsed, so the custom variables are available.

Palettes:
- Dark / Sepia — the app's original two looks.
- Compline / Lauds — contemplative dark/light palettes (joshuablais/compline).
- Vigil — true-black AMOLED (longestmt/librelift).
"""

from __future__ import annotations

from textual.theme import Theme

# Display names shown when cycling themes (T).
THEME_LABELS: dict[str, str] = {
    "osb-dark": "Dark",
    "osb-sepia": "Sepia",
    "osb-compline": "Compline",
    "osb-lauds": "Lauds",
    "osb-vigil": "Vigil",
}

# Palette keys every theme defines (consumed as $name in the .tcss files).
_PALETTES: dict[str, dict[str, str]] = {
    "osb-dark": {
        "bg": "#1a1a1a", "surface": "#242424", "surface-alt": "#2e2e2e", "border": "#3a3a3a",
        "accent": "#c9a84c", "accent-dim": "#8a6f2e",
        "text": "#e8e0d0", "text-muted": "#888880", "text-verse": "#d4cdc0",
        "hl-yellow": "#4a3c00", "hl-green": "#1a3a1a", "hl-blue": "#0a2040", "hl-pink": "#3a1028",
        "search-current": "#3a3000", "warning": "#c0803a", "chat-user-bg": "#2a2010",
    },
    "osb-sepia": {
        "bg": "#2c2416", "surface": "#362d1e", "surface-alt": "#403528", "border": "#5a4a30",
        "accent": "#d4a84c", "accent-dim": "#9a7230",
        "text": "#e8dcc0", "text-muted": "#9a8060", "text-verse": "#ddd0b0",
        "hl-yellow": "#5a4800", "hl-green": "#243824", "hl-blue": "#142848", "hl-pink": "#481828",
        "search-current": "#3a2800", "warning": "#c0803a", "chat-user-bg": "#403528",
    },
    "osb-compline": {
        "bg": "#1a1d21", "surface": "#1f2229", "surface-alt": "#2a2e34", "border": "#3d424a",
        "accent": "#d4ccb4", "accent-dim": "#9a9176",
        "text": "#f0efeb", "text-muted": "#8b919a", "text-verse": "#d6d4cc",
        "hl-yellow": "#3d3a2a", "hl-green": "#2a3a2e", "hl-blue": "#2a3340", "hl-pink": "#3d2a2e",
        "search-current": "#44402e", "warning": "#d4b48c", "chat-user-bg": "#2a2e34",
    },
    "osb-lauds": {
        "bg": "#f0efeb", "surface": "#e7e6e1", "surface-alt": "#dcdbd3", "border": "#c9c7bd",
        "accent": "#7a6d5a", "accent-dim": "#9a9182",
        "text": "#1a1d21", "text-muted": "#6a685e", "text-verse": "#2e2e2a",
        "hl-yellow": "#ece4c0", "hl-green": "#d6e2d2", "hl-blue": "#d2dbe4", "hl-pink": "#ecd6d6",
        "search-current": "#e6dcb4", "warning": "#8a5a2e", "chat-user-bg": "#e7e6e1",
    },
    "osb-vigil": {
        "bg": "#000000", "surface": "#0a0a0a", "surface-alt": "#141414", "border": "#1a1a1a",
        "accent": "#d4ccb4", "accent-dim": "#9a9176",
        "text": "#f0efeb", "text-muted": "#8b919a", "text-verse": "#d6d4cc",
        "hl-yellow": "#2e2a18", "hl-green": "#16241a", "hl-blue": "#14202e", "hl-pink": "#2a1418",
        "search-current": "#2e2a14", "warning": "#d4b48c", "chat-user-bg": "#141414",
    },
}

_LIGHT = {"osb-lauds"}


def _build(name: str, p: dict[str, str]) -> Theme:
    return Theme(
        name=name,
        dark=name not in _LIGHT,
        primary=p["accent"],
        secondary=p["text-muted"],
        accent=p["accent"],
        foreground=p["text"],
        background=p["bg"],
        surface=p["surface"],
        panel=p["surface-alt"],
        warning=p["warning"],
        error="#cdacac",
        success="#b8c4b8",
        variables=dict(p),
    )


OSB_THEMES: list[Theme] = [_build(name, p) for name, p in _PALETTES.items()]
THEME_NAMES: list[str] = [t.name for t in OSB_THEMES]
DEFAULT_THEME = "osb-dark"
