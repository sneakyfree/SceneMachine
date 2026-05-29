"""
Pure-logic tests for TextOverlay — timing conversions, style accessors, and
position-to-pixel mapping. Transient instances, no DB.
"""

from scenemachine.models.text_overlay import (
    TextOverlay,
    TextOverlayType,
    TextPosition,
)


def _overlay(**kw):
    o = TextOverlay(
        overlay_type=kw.pop("overlay_type", TextOverlayType.TITLE),
        text=kw.pop("text", "Hello"),
        position=kw.pop("position", TextPosition.CENTER),
    )
    for k, v in kw.items():
        setattr(o, k, v)
    return o


def test_timing_conversions():
    o = _overlay(start_time_ms=2000, duration_ms=5000)
    assert o.start_time_seconds == 2.0
    assert o.duration_seconds == 5.0
    assert o.end_time_ms == 7000
    assert o.end_time_seconds == 7.0


def test_style_accessors_defaults():
    o = _overlay(style=None)
    assert o.font_family == "Arial"
    assert o.font_size == 48
    assert o.font_color == "#FFFFFF"
    assert o.background_color == "#000000"
    assert o.background_opacity == 0.0


def test_style_accessors_from_style_dict():
    o = _overlay(
        style={
            "fontFamily": "Helvetica",
            "fontSize": 72,
            "color": "#FF0000",
            "backgroundColor": "#222222",
            "backgroundOpacity": 0.5,
        }
    )
    assert o.font_family == "Helvetica"
    assert o.font_size == 72
    assert o.font_color == "#FF0000"
    assert o.background_color == "#222222"
    assert o.background_opacity == 0.5


def test_position_coords_corners_and_center():
    w, h = 1000, 500
    assert _overlay(position=TextPosition.TOP_LEFT).get_position_coords(w, h) == (50, 25)
    assert _overlay(position=TextPosition.CENTER).get_position_coords(w, h) == (500, 250)
    assert _overlay(position=TextPosition.TOP_RIGHT).get_position_coords(w, h) == (950, 25)


def test_position_coords_custom():
    o = _overlay(position=TextPosition.CUSTOM, custom_x=50, custom_y=50)
    assert o.get_position_coords(1000, 500) == (500, 250)
