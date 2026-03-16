"""SplashScreen — startup splash with Orthodox cross and animated border glow."""

from __future__ import annotations

import math

from textual.app import ComposeResult
from textual.color import Color
from textual.screen import Screen
from textual.widgets import Static

_ART    = "☦\n\nOrthodox Study Bible"
_PRAYER = "Lord Jesus Christ, Son of God, have mercy on me, a sinner."

_DIM    = Color.parse("#4a3a12")   # unlit border segment
_GOLD   = Color.parse("#c9a84c")   # resting text + mid-glow
_BRIGHT = Color.parse("#ffffff")   # peak glow
_DIM_GOLD = Color.parse("#7a6020") # prayer text colour (softer)

# ── Timing ────────────────────────────────────────────────────────────────────
_FADE_IN    = 0.28   # opacity 0→1  (out_expo: snaps in, settles smoothly)
_COLOR_DUR  = 0.50   # color white→gold  (out_circ: organic)
_HOLD       = 3.50   # active glow period (extended for typewriter prayer)
_FADE_OUT   = 0.32   # opacity 1→0  (in_expo: crisp exit)

# ── Typewriter ────────────────────────────────────────────────────────────────
_TYPE_TICK  = 0.035  # seconds per character (~28 chars/s)

# ── Border glow ───────────────────────────────────────────────────────────────
_TICK       = 0.050  # ~20 fps
_SPD_A      = 0.24   # primary glow: radians per tick  (CW, ~1.3 s/lap)
_SPD_B      = 0.09   # secondary glow: radians per tick (CCW, slower)
_FALLOFF    = 2.8    # Gaussian falloff sharpness (higher = sharper bright spot)
_SEC_STR    = 0.38   # secondary glow strength relative to primary
_BREATH_AMP = 0.08   # breathing-pulse amplitude (subtle)
_BREATH_HZ  = 2.8    # breathing-pulse frequency (radians per second)

_SIDES = [
    ("border_top",    0.0),
    ("border_right",  math.pi * 0.5),
    ("border_bottom", math.pi),
    ("border_left",   math.pi * 1.5),
]


def _angular_dist(a: float, b: float) -> float:
    """Shortest angular distance between two angles on [0, 2π)."""
    d = abs(a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d)


class SplashScreen(Screen):
    """Startup splash: ☦ symbol + title, bordered box, rotating glow."""

    AUTO_FOCUS = ""
    DEFAULT_CSS = """
    SplashScreen {
        align: center middle;
    }
    #splash-box {
        border: double $accent;
        padding: 2 6;
        min-width: 30;
        width: auto;
        height: auto;
        text-align: center;
        text-style: bold;
    }
    #prayer-text {
        text-align: center;
        color: #7a6020;
        padding: 1 0 0 0;
        text-style: italic;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._fading_out = False
        self._angle_a = 0.0      # primary glow angle
        self._angle_b = math.pi  # secondary glow starts opposite
        self._elapsed = 0.0      # for breathing pulse
        self._glow_timer = None
        self._type_timer = None
        self._type_idx = 0       # chars revealed so far

    def compose(self) -> ComposeResult:
        yield Static(_ART, id="splash-box")
        yield Static("", id="prayer-text")

    def on_mount(self) -> None:
        box = self.query_one("#splash-box", Static)
        box.styles.opacity = 0.0
        box.styles.color = _BRIGHT

        # Stage 1: snap in (out_expo) + color flash white→gold (out_circ)
        box.styles.animate("opacity", 1.0, duration=_FADE_IN, easing="out_expo")
        box.styles.animate("color", _GOLD, duration=_COLOR_DUR, easing="out_circ")

        # Stage 2: start border glow + typewriter prayer, schedule dismiss
        self.set_timer(_FADE_IN, self._start_glow)
        self.set_timer(_FADE_IN, self._start_typewriter)
        self.set_timer(_FADE_IN + _HOLD, self._fade_out)

    # ── Border glow ──────────────────────────────────────────────────────────

    def _start_glow(self) -> None:
        self._glow_timer = self.set_interval(_TICK, self._tick_glow)

    def _tick_glow(self) -> None:
        # Advance angles: A clockwise, B counter-clockwise
        self._angle_a = (self._angle_a + _SPD_A) % (2 * math.pi)
        self._angle_b = (self._angle_b - _SPD_B) % (2 * math.pi)
        self._elapsed += _TICK

        # Breathing pulse: gentle sine oscillation over global brightness
        breath = _BREATH_AMP * math.sin(self._elapsed * _BREATH_HZ)

        try:
            box = self.query_one("#splash-box", Static)
        except Exception:
            return

        for attr, center in _SIDES:
            # Gaussian-shaped glow for each source (physically plausible falloff)
            dist_a = _angular_dist(self._angle_a, center)
            dist_b = _angular_dist(self._angle_b, center)
            glow_a = math.exp(-dist_a * _FALLOFF)
            glow_b = math.exp(-dist_b * _FALLOFF) * _SEC_STR

            brightness = min(1.0, max(0.0, glow_a + glow_b + breath))
            color = _DIM.blend(_BRIGHT, brightness)
            setattr(box.styles, attr, ("double", color))

    # ── Typewriter ────────────────────────────────────────────────────────────

    def _start_typewriter(self) -> None:
        self._type_timer = self.set_interval(_TYPE_TICK, self._tick_type)

    def _tick_type(self) -> None:
        self._type_idx += 1
        try:
            label = self.query_one("#prayer-text", Static)
            label.update(_PRAYER[: self._type_idx])
        except Exception:
            pass
        if self._type_idx >= len(_PRAYER):
            if self._type_timer is not None:
                self._type_timer.stop()
                self._type_timer = None

    def _stop_glow(self) -> None:
        if self._glow_timer is not None:
            self._glow_timer.stop()
            self._glow_timer = None
        if self._type_timer is not None:
            self._type_timer.stop()
            self._type_timer = None

    # ── Exit ─────────────────────────────────────────────────────────────────

    def _fade_out(self) -> None:
        if self._fading_out:
            return
        self._fading_out = True
        self._stop_glow()
        try:
            box = self.query_one("#splash-box", Static)
            box.styles.animate(
                "opacity", 0.0, duration=_FADE_OUT,
                easing="in_expo", on_complete=self.dismiss,
            )
        except Exception:
            self.dismiss()

    def on_key(self, _event) -> None:
        self._fade_out()
