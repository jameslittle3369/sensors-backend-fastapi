"""Sun/moon geometry and the house-compass SVG renderer for the almanac slice.

Kept out of app/routers/almanac.py so the geometry is directly unit-testable
without going through the HTTP layer.

api.ipgeolocation.io's /v3/astronomy has no `time` parameter -- its
sun/moon altitude+azimuth fields are the position at the instant of the
request, not at any point during the requested date (see app/models/
almanac.py's docstring). Every azimuth and "current sun position" figure
actually used here is computed locally with astral instead.
"""

from __future__ import annotations

import base64
import struct
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from html import escape
from math import atan2, cos, degrees, hypot, pi, radians, sin, sqrt
from typing import Callable

from astral import Observer
from astral import moon as astral_moon
from astral import sun as astral_sun

from app.core.config import Settings


def observer_from_settings(settings: Settings) -> Observer:
    return Observer(
        latitude=float(settings.latitude),
        longitude=float(settings.longitude),
        elevation=float(settings.elevation_m),
    )


def _round2(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _azimuth_or_none(fn: Callable[[Observer, datetime], float], observer: Observer, at: datetime | None) -> Decimal | None:
    """Azimuth at `at` via `fn` (astral.sun.azimuth or astral.moon.azimuth),
    or None if `at` is None -- the API's "-" sentinel for a day the moon
    doesn't rise/set, already normalised to None before this is called."""
    if at is None:
        return None
    return _round2(fn(observer, _utc(at)))


def _utc(at: datetime) -> datetime:
    """astral.moon's azimuth/elevation ignore tzinfo and read the wall-clock
    fields as UTC (astral.sun's convert properly) -- so a 05:23 America/
    Chicago moonrise was being evaluated at 05:23 UTC, six hours early.
    Converting every time to UTC first is right for both."""
    return at.astimezone(timezone.utc)


def rise_set_azimuths(
    observer: Observer,
    *,
    sunrise_at: datetime | None,
    sunset_at: datetime | None,
    moonrise_at: datetime | None,
    moonset_at: datetime | None,
) -> dict[str, Decimal | None]:
    """The four azimuths this whole feature exists to produce -- none of
    them come from the API, all computed locally from the API's own
    rise/set *times* (or astral's own sunrise/sunset/moonrise/moonset when
    there's no stored row at all -- see compute_rise_set below)."""
    return {
        "sunrise_azimuth_deg": _azimuth_or_none(astral_sun.azimuth, observer, sunrise_at),
        "sunset_azimuth_deg": _azimuth_or_none(astral_sun.azimuth, observer, sunset_at),
        "moonrise_azimuth_deg": _azimuth_or_none(astral_moon.azimuth, observer, moonrise_at),
        "moonset_azimuth_deg": _azimuth_or_none(astral_moon.azimuth, observer, moonset_at),
    }


def compute_rise_set(observer: Observer, day: date, tzinfo) -> dict[str, datetime | None]:
    """Sunrise/sunset for `day` straight from astral -- used by the compass
    endpoint when there's no stored AlmanacDay row for that date (any date
    renders, per the Grafana panel's design; a stored row only adds the
    API-sourced extras). Astral raises on the (practically irrelevant for
    this project's latitudes) case of a sun that never rises or sets that
    day -- caught and reported as None rather than propagating."""
    result: dict[str, datetime | None] = {}
    for name, fn in (("sunrise_at", astral_sun.sunrise), ("sunset_at", astral_sun.sunset)):
        try:
            result[name] = fn(observer, day, tzinfo=tzinfo)
        except ValueError:
            result[name] = None
    return result


def sun_now(observer: Observer, at: datetime) -> tuple[Decimal, Decimal]:
    """(azimuth_deg, elevation_deg) of the sun at `at`."""
    return _round2(astral_sun.azimuth(observer, at)), _round2(astral_sun.elevation(observer, at))


def moon_now(observer: Observer, at: datetime) -> tuple[Decimal, Decimal]:
    """(azimuth_deg, elevation_deg) of the moon at `at`."""
    return _round2(astral_moon.azimuth(observer, _utc(at))), _round2(astral_moon.elevation(observer, _utc(at)))


def compute_moon_rise_set(observer: Observer, day: date, tzinfo) -> dict[str, datetime | None]:
    """Moonrise/moonset for `day` from astral -- the fallback when there's
    no stored row with the API's own times. Either can legitimately be
    None: on roughly one day a month the moon doesn't rise (or set) at all
    within a given calendar day."""
    result: dict[str, datetime | None] = {}
    for name, fn in (("moonrise_at", astral_moon.moonrise), ("moonset_at", astral_moon.moonset)):
        try:
            result[name] = fn(observer, day, tzinfo=tzinfo)
        except ValueError:
            result[name] = None
    return result


# astral.moon.phase() is on a 0-28 scale (0 new, 7 first quarter, 14 full,
# 21 last quarter), not days of the ~29.53-day synodic month.
_ASTRAL_PHASE_PERIOD = 28.0


def moon_illumination(day: date) -> tuple[float, bool]:
    """(illuminated fraction 0..1, waxing?) for `day`."""
    age = astral_moon.phase(day)
    fraction = (1 - cos(2 * pi * age / _ASTRAL_PHASE_PERIOD)) / 2
    return fraction, age < _ASTRAL_PHASE_PERIOD / 2


def moon_phase_name(fraction: float, waxing: bool) -> str:
    if fraction < 0.02:
        return "New Moon"
    if fraction > 0.98:
        return "Full Moon"
    if abs(fraction - 0.5) < 0.03:
        return "First Quarter" if waxing else "Last Quarter"
    return f"{'Waxing' if waxing else 'Waning'} {'Crescent' if fraction < 0.5 else 'Gibbous'}"


# --- Image sniffing -----------------------------------------------------
# Deliberately not a dependency on Pillow/an image library -- the compass
# only needs the pixel dimensions (to size the SVG viewBox so the overlay
# lines up with the photo with no stretching/cropping) and a MIME type for
# the data: URI. PNG and JPEG cover every realistic source for a Google
# Maps screenshot.


class UnsupportedImageError(ValueError):
    pass


def sniff_image(data: bytes) -> tuple[str, int, int]:
    """(mime_type, width, height). Raises UnsupportedImageError for
    anything that isn't PNG or JPEG."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return "image/png", width, height
    if data[:2] == b"\xff\xd8":
        return "image/jpeg", *_jpeg_dimensions(data)
    raise UnsupportedImageError("House image must be PNG or JPEG.")


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    # Scan JFIF markers for a Start-Of-Frame segment (0xC0-0xCF, excluding
    # 0xC4 DHT / 0xC8 JPG / 0xCC DAC, which share the marker range but
    # aren't SOF). The SOF payload is: 1 byte precision, 2 bytes height,
    # 2 bytes width, both big-endian.
    pos = 2
    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9):  # SOI / EOI: no length field
            pos += 2
            continue
        (length,) = struct.unpack(">H", data[pos + 2 : pos + 4])
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[pos + 5 : pos + 9])
            return width, height
        pos += 2 + length
    raise UnsupportedImageError("Could not find a JPEG Start-Of-Frame segment.")


# --- SVG rendering --------------------------------------------------------
# Colours, sizes and layout rules were settled interactively with
# sensors-ansible/tools/compass-helper/ (2026-11-07) -- change them there
# first to preview, then copy the values here. Sizes are fractions of the
# ring radius, so everything scales with the photo.

_RING_COLOR = "#fff700"  # ring, ticks, N/E/S/W
_SUNRISE_COLOR = "#f59700"
_SUNSET_COLOR = "#d82613"
_CURRENT_SUN_COLOR = "#ffd54a"
_SWEPT_ARC_COLOR = "#ffd54a"
_REMAINING_ARC_COLOR = "#f5a623"
_READOUT_COLOR = "#ffffff"
_MOON_TEXT_COLOR = "#9fd3ff"  # moon readout line, moonrise/moonset rays and arc
_MOON_LIT_COLOR = "#f4f1de"
_MOON_DARK_COLOR = "#1b1d22"

_CARDINAL_SIZE = 0.09
_RAY_LABEL_SIZE = 0.09
_READOUT_SIZE = 0.09
_MOON_TEXT_SIZE = 0.075  # moon readout + the az/el labels beside the sun and moon
_SUN_DOT_SIZE = 0.06
_MOON_DISC_SIZE = 0.08
_MOON_ARC_RADIUS = 0.88  # inside the ring, so it doesn't sit on the sun's arc
_BELOW_HORIZON_OPACITY = 0.75
_OUTLINE_PX = 3
_LABEL_PAD = _OUTLINE_PX + 6  # gap between the ring and text placed outside it

_FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
_HALO = f'style="paint-order: stroke; stroke: #000; stroke-width: {_OUTLINE_PX}px; stroke-opacity: 0.6;"'
_NBSP = " "
# Wrapping only breaks at ordinary spaces, so non-breaking ones keep each
# label with its value ("Az 139.4°") and glue the " ·" separator to the
# value before it -- a wrapped line never starts with a dot or a bare number.
_DOT = f"{_NBSP}·"


def _point(cx: float, cy: float, r: float, azimuth_deg: float, north_offset_deg: float) -> tuple[float, float]:
    angle = radians(azimuth_deg + north_offset_deg)
    return cx + r * sin(angle), cy - r * cos(angle)


def _arc_path(cx: float, cy: float, r: float, start_deg: float, end_deg: float, north_offset_deg: float) -> str | None:
    """SVG path for the clockwise arc from start_deg to end_deg (compass
    bearings), or None if the sweep is zero (nothing to draw)."""
    delta = (end_deg - start_deg) % 360
    if delta == 0:
        return None
    large_arc = 1 if delta > 180 else 0
    x1, y1 = _point(cx, cy, r, start_deg, north_offset_deg)
    x2, y2 = _point(cx, cy, r, end_deg, north_offset_deg)
    return f"M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large_arc} 1 {x2:.2f} {y2:.2f}"


def _format_local_time(dt: datetime | None) -> str:
    return dt.strftime("%H:%M") if dt else "--:--"


def _signed(value: float) -> str:
    return f"{'+' if value >= 0 else '−'}{abs(value):.1f}"


def _format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    return f"{minutes // 60}h{_NBSP}{minutes % 60}m"


# --- Text measurement and placement ---------------------------------------
# No browser here to measure text, so widths are estimated per character
# (em fractions for a typical sans-serif), then padded slightly -- wrapping
# a word early is better than running into the ring. The helper page
# measures exactly, so its wrap points can differ by a word.

_NARROW_CHARS = set("iljtfrI.,:;'|!()[] ·°" + _NBSP)
_WIDE_CHARS = set("MWmw%@")


def _text_width(text: str, size: float, bold: bool = False) -> float:
    em = 0.0
    for ch in text:
        if ch in _NARROW_CHARS:
            em += 0.32
        elif ch in _WIDE_CHARS:
            em += 0.85
        elif ch.isupper():
            em += 0.68
        elif ch.isdigit():
            em += 0.58
        else:
            em += 0.54
    return em * size * (1.06 if bold else 1.0) * 1.05


# (x0, y0, x1, y1) in image pixels.
_Box = tuple[float, float, float, float]


def _overlaps(a: _Box, b: _Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _text_el(x: float, y: float, lines: list[str], size: float, fill: str, anchor: str, valign: str, bold: bool = False) -> str:
    """Multi-line <text>. valign 'mid': lines centred vertically on y;
    'top': first baseline at y."""
    line_height = size * 1.2
    y0 = y - (len(lines) - 1) * line_height / 2 if valign == "mid" else y
    baseline = ' dominant-baseline="middle"' if valign == "mid" else ""
    weight = ' font-weight="bold"' if bold else ""
    spans = "".join(
        f'<tspan x="{x:.2f}"{f" dy=\"{line_height:.2f}\"" if i else ""}>{escape(line)}</tspan>' for i, line in enumerate(lines)
    )
    return (
        f'<text x="{x:.2f}" y="{y0:.2f}" fill="{fill}" font-size="{size:.1f}"{weight} '
        f'text-anchor="{anchor}"{baseline} {_HALO}>{spans}</text>'
    )


def _place_ray_label(
    *,
    cx: float,
    cy: float,
    r: float,
    width: int,
    height: int,
    azimuth: float,
    north_offset_deg: float,
    caption: str,
    when: datetime | None,
    color: str,
    size: float,
    boxes: list[_Box],
) -> str:
    """A rise/set label just outside the ring, anchored on the side facing
    away from it so the text grows outward instead of back across the
    compass. If that spot overlaps an earlier label, leaves the image, or
    touches the ring, it tries one line vs. two, then nudges up/down and
    further out; a label that had to move gets a leader line back to
    where its ray meets the ring. Appends the chosen box to `boxes`."""
    bearing = f"({azimuth:.1f}°)"
    one = [f"{caption} {_format_local_time(when)} {bearing}"]
    two = [f"{caption} {_format_local_time(when)}", bearing]
    s, c = sin(radians(azimuth + north_offset_deg)), cos(radians(azimuth + north_offset_deg))
    # Near due N/S there's no outward side horizontally -- centre the label
    # and push it out vertically instead.
    anchor = "middle" if abs(s) < 0.35 else ("start" if s > 0 else "end")

    def place(lines: list[str], extra: float, dy: float) -> tuple[float, float, _Box, bool]:
        line_w = max(_text_width(line, size) for line in lines)
        block_h = size * 1.2 * len(lines)
        lx, ly0 = _point(cx, cy, r + _LABEL_PAD + extra, azimuth, north_offset_deg)
        ly = (ly0 - (1 if c > 0 else -1 if c < 0 else 0) * block_h / 2 if anchor == "middle" else ly0) + dy
        x0 = lx if anchor == "start" else lx - line_w if anchor == "end" else lx - line_w / 2
        box = (x0, ly - block_h / 2, x0 + line_w, ly + block_h / 2)
        in_image = box[0] >= 0 and box[1] >= 0 and box[2] <= width and box[3] <= height
        nearest_x, nearest_y = min(max(cx, box[0]), box[2]), min(max(cy, box[1]), box[3])
        off_ring = hypot(nearest_x - cx, nearest_y - cy) >= r + 2
        free = not any(_overlaps(box, other) for other in boxes)
        return lx, ly, box, in_image and off_ring and free

    steps: list[tuple[float, float]] = [(0.0, 0.0)]
    for extra in (0.0, r * 0.12, r * 0.25):
        for i in range(1, 6):
            for sign in (1, -1):
                steps.append((extra, sign * i * size * 1.25))
    steps += [(r * 0.12, 0.0), (r * 0.25, 0.0)]

    chosen = None
    for extra, dy in steps:
        for lines in (one, two):
            lx, ly, box, ok = place(lines, extra, dy)
            if ok:
                chosen = (lx, ly, box, lines, extra != 0 or dy != 0)
                break
        if chosen:
            break
    if chosen is None:  # nowhere clear -- fall back to the default two-line spot
        lx, ly, box, _ = place(two, 0.0, 0.0)
        chosen = (lx, ly, box, two, False)

    lx, ly, box, lines, moved = chosen
    boxes.append(box)
    parts = []
    if moved:
        x1, y1 = _point(cx, cy, r + 3, azimuth, north_offset_deg)
        ex = box[0] - 3 if anchor == "start" else box[2] + 3 if anchor == "end" else lx
        ey = (box[3] + 3 if c > 0 else box[1] - 3) if anchor == "middle" else ly
        parts.append(
            f'<circle cx="{x1:.2f}" cy="{y1:.2f}" r="2.5" fill="{color}" />'
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" stroke="#000" '
            f'stroke-width="{1.5 + _OUTLINE_PX}" stroke-opacity="0.5" />'
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" stroke="{color}" '
            f'stroke-width="1.5" stroke-opacity="0.9" />'
        )
    parts.append(_text_el(lx, ly, lines, size, color, anchor, "mid"))
    return "".join(parts)


def _moon_disc(x: float, y: float, radius: float, fraction: float, rotation_deg: float, opacity: float, dashed: bool) -> str:
    """Moon with its phase: drawn lit-side-right (+x), then rotated so the
    lit side points `rotation_deg` (screen degrees, toward the sun)."""
    if fraction <= 0.005:
        lit = ""
    elif fraction >= 0.995:
        lit = f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{_MOON_LIT_COLOR}" />'
    else:
        # Semicircle on the lit side, closed by the terminator: a half
        # ellipse bulging toward the dark side when gibbous, the lit side
        # when crescent.
        terminator_rx = radius * abs(2 * fraction - 1)
        sweep = 1 if fraction > 0.5 else 0
        lit = (
            f'<path fill="{_MOON_LIT_COLOR}" d="M {x:.2f} {y - radius:.2f} '
            f"A {radius:.2f} {radius:.2f} 0 0 1 {x:.2f} {y + radius:.2f} "
            f'A {terminator_rx:.2f} {radius:.2f} 0 0 {sweep} {x:.2f} {y - radius:.2f} Z" />'
        )
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    return (
        f'<g opacity="{opacity}" transform="rotate({rotation_deg:.2f} {x:.2f} {y:.2f})">'
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{_MOON_DARK_COLOR}" fill-opacity="0.85" />'
        f"{lit}"
        # Light rim, so a thin crescent's mostly-dark disc still shows up
        # against dark trees.
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="none" stroke="{_MOON_LIT_COLOR}" '
        f'stroke-width="1.5" stroke-opacity="0.7"{dash} />'
        "</g>"
    )


def render_compass_svg(
    *,
    image_bytes: bytes,
    day: date,
    is_today: bool,
    sunrise_at: datetime | None,
    sunset_at: datetime | None,
    sunrise_azimuth_deg: Decimal | None,
    sunset_azimuth_deg: Decimal | None,
    current_azimuth_deg: Decimal | None,
    current_elevation_deg: Decimal | None,
    north_offset_deg: float = 0.0,
    center_x_pct: float = 0.5,
    center_y_pct: float = 0.5,
    radius_pct: float = 0.42,
    now_local: datetime | None = None,
    moonrise_at: datetime | None = None,
    moonset_at: datetime | None = None,
    moonrise_azimuth_deg: Decimal | None = None,
    moonset_azimuth_deg: Decimal | None = None,
    moon_azimuth_deg: Decimal | None = None,
    moon_elevation_deg: Decimal | None = None,
    moon_fraction: float | None = None,
    moon_waxing: bool | None = None,
) -> str:
    """The whole panel image: the house photo at its native resolution,
    with a compass ring, sunrise/sunset and moonrise/moonset rays, the
    sun's and moon's arcs and (when `is_today`) their current positions,
    plus a sun/moon readout in the top-left corner. Positions use
    r·cos(elevation) from the centre; a body below the horizon is still
    drawn, see-through with a dashed outline."""
    mime, width, height = sniff_image(image_bytes)
    data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"

    cx = width * center_x_pct
    cy = height * center_y_pct
    r = min(width, height) * radius_pct
    card_size, ray_size = r * _CARDINAL_SIZE, r * _RAY_LABEL_SIZE
    readout_size, moon_text_size = r * _READOUT_SIZE, r * _MOON_TEXT_SIZE

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="{_FONT_FAMILY}">',
        f'<image x="0" y="0" width="{width}" height="{height}" href="{data_uri}" />',
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="none" '
        f'stroke="{_RING_COLOR}" stroke-width="2" stroke-opacity="0.85" />',
    ]
    # Text goes last so it sits on top of every line and arc.
    labels: list[str] = []
    boxes: list[_Box] = []

    # Tick marks every 30 degrees, cardinal points labelled.
    for tick_deg in range(0, 360, 30):
        x1, y1 = _point(cx, cy, r * 0.92, tick_deg, north_offset_deg)
        x2, y2 = _point(cx, cy, r, tick_deg, north_offset_deg)
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{_RING_COLOR}" stroke-width="2" stroke-opacity="0.85" />'
        )
    for tick_deg, label in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
        lx, ly = _point(cx, cy, r * 1.12, tick_deg, north_offset_deg)
        labels.append(_text_el(lx, ly, [label], card_size, _RING_COLOR, "middle", "mid", bold=True))
        half_w = _text_width(label, card_size, bold=True) / 2
        boxes.append((lx - half_w, ly - card_size / 2, lx + half_w, ly + card_size / 2))

    # Rise/set rays. Sun first, so its labels get first pick of the spots
    # next to the ring; the moon's (dashed, thinner) move if they clash.
    rays = [
        (sunrise_azimuth_deg, _SUNRISE_COLOR, "Sunrise", sunrise_at, False),
        (sunset_azimuth_deg, _SUNSET_COLOR, "Sunset", sunset_at, False),
        (moonrise_azimuth_deg, _MOON_TEXT_COLOR, "Moonrise", moonrise_at, True),
        (moonset_azimuth_deg, _MOON_TEXT_COLOR, "Moonset", moonset_at, True),
    ]
    for azimuth, color, caption, when, is_moon in rays:
        if azimuth is None:
            continue
        az = float(azimuth)
        x, y = _point(cx, cy, r, az, north_offset_deg)
        style = 'stroke-width="2" stroke-opacity="0.85" stroke-dasharray="8 5"' if is_moon else 'stroke-width="3" stroke-opacity="0.9"'
        parts.append(f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{x:.2f}" y2="{y:.2f}" stroke="{color}" {style} />')
        labels.append(
            _place_ray_label(
                cx=cx, cy=cy, r=r, width=width, height=height, azimuth=az, north_offset_deg=north_offset_deg,
                caption=caption, when=when, color=color, size=ray_size, boxes=boxes,
            )
        )

    # Sun arc.
    show_now = is_today and current_azimuth_deg is not None
    if show_now and sunrise_azimuth_deg is not None and sunset_azimuth_deg is not None:
        cur = float(current_azimuth_deg)
        swept = _arc_path(cx, cy, r, float(sunrise_azimuth_deg), cur, north_offset_deg)
        remaining = _arc_path(cx, cy, r, cur, float(sunset_azimuth_deg), north_offset_deg)
        if swept:
            parts.append(f'<path d="{swept}" fill="none" stroke="{_SWEPT_ARC_COLOR}" stroke-width="5" stroke-opacity="0.9" />')
        if remaining:
            parts.append(
                f'<path d="{remaining}" fill="none" stroke="{_REMAINING_ARC_COLOR}" '
                f'stroke-width="3" stroke-opacity="0.35" stroke-dasharray="6,6" />'
            )
    elif sunrise_azimuth_deg is not None and sunset_azimuth_deg is not None:
        full_day = _arc_path(cx, cy, r, float(sunrise_azimuth_deg), float(sunset_azimuth_deg), north_offset_deg)
        if full_day:
            parts.append(f'<path d="{full_day}" fill="none" stroke="{_SWEPT_ARC_COLOR}" stroke-width="4" stroke-opacity="0.55" />')

    # Moon arc, moonrise -> moonset clockwise on its own smaller radius.
    # Solid up to the moon while it's up, faint and dashed otherwise.
    if moonrise_azimuth_deg is not None and moonset_azimuth_deg is not None:
        rm = r * _MOON_ARC_RADIUS
        mr, ms = float(moonrise_azimuth_deg), float(moonset_azimuth_deg)
        faint = f'fill="none" stroke="{_MOON_TEXT_COLOR}" stroke-width="3" stroke-opacity="0.35" stroke-dasharray="6,6"'
        moon_up = is_today and moon_azimuth_deg is not None and moon_elevation_deg is not None and float(moon_elevation_deg) >= 0
        if moon_up:
            swept = _arc_path(cx, cy, rm, mr, float(moon_azimuth_deg), north_offset_deg)
            remaining = _arc_path(cx, cy, rm, float(moon_azimuth_deg), ms, north_offset_deg)
            if swept:
                parts.append(f'<path d="{swept}" fill="none" stroke="{_MOON_TEXT_COLOR}" stroke-width="4" stroke-opacity="0.85" />')
            if remaining:
                parts.append(f'<path d="{remaining}" {faint} />')
        else:
            full = _arc_path(cx, cy, rm, mr, ms, north_offset_deg)
            if full:
                parts.append(f'<path d="{full}" {faint} />')

    # Current sun and moon -- drawn even below the horizon (see-through,
    # dashed outline), with their az/el beside them.
    sun_xy = None
    if show_now:
        cur = float(current_azimuth_deg)
        elevation = float(current_elevation_deg) if current_elevation_deg is not None else 0.0
        sx, sy = _point(cx, cy, r * cos(radians(elevation)), cur, north_offset_deg)
        sun_xy = (sx, sy)
        dot_r = r * _SUN_DOT_SIZE
        if elevation < 0:
            parts.append(
                f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{dot_r:.2f}" fill="{_CURRENT_SUN_COLOR}" '
                f'opacity="{_BELOW_HORIZON_OPACITY}" stroke="{_CURRENT_SUN_COLOR}" stroke-width="2" stroke-dasharray="4 3" />'
            )
        else:
            parts.append(
                f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{dot_r:.2f}" fill="{_CURRENT_SUN_COLOR}" '
                f'stroke="#000" stroke-width="1.5" stroke-opacity="0.5" />'
            )
        labels.append(
            _text_el(sx + dot_r + 4, sy, [f"{cur:.1f}° {_signed(elevation)}°"], moon_text_size, _CURRENT_SUN_COLOR, "start", "mid")
        )
    if is_today and moon_azimuth_deg is not None and moon_elevation_deg is not None and moon_fraction is not None:
        maz, mel = float(moon_azimuth_deg), float(moon_elevation_deg)
        mx, my = _point(cx, cy, r * cos(radians(mel)), maz, north_offset_deg)
        disc_r = r * _MOON_DISC_SIZE
        # Lit side faces the sun's spot on the compass; without one, the
        # northern-hemisphere view (waxing lit on the right).
        if sun_xy is not None:
            rotation = degrees(atan2(sun_xy[1] - my, sun_xy[0] - mx))
        else:
            rotation = 0.0 if moon_waxing else 180.0
        below = mel < 0
        parts.append(_moon_disc(mx, my, disc_r, moon_fraction, rotation, _BELOW_HORIZON_OPACITY if below else 1, below))
        labels.append(_text_el(mx + disc_r + 4, my, [f"{maz:.1f}° {_signed(mel)}°"], moon_text_size, _MOON_LIT_COLOR, "start", "mid"))

    # Top-left readout. Each line is word-wrapped to the room between the
    # image's left edge and the compass (ring + N/E/S/W labels) at that
    # line's height, so text never runs across the compass.
    keep_out = r * 1.12 + card_size * 0.6
    rx = width * 0.02
    baseline = height * 0.05

    def room(y_top: float, y_bottom: float) -> float:
        dy = y_top - cy if cy < y_top else cy - y_bottom if cy > y_bottom else 0.0
        limit = width if dy >= keep_out else cx - sqrt(keep_out**2 - dy**2)
        return min(limit, width) - rx - _LABEL_PAD

    def block(lines: list[str], size: float, color: str) -> None:
        nonlocal baseline
        line_height = size * 1.2
        out: list[str] = []
        for text in lines:
            current = ""
            for word in text.split(" "):
                if not word:
                    continue
                attempt = f"{current} {word}" if current else word
                y = baseline + len(out) * line_height
                if not current or _text_width(attempt, size) <= room(y - size * 0.8, y + size * 0.25):
                    current = attempt
                else:
                    out.append(current)
                    current = word
            if current:
                out.append(current)
        labels.append(_text_el(rx, baseline, out, size, color, "start", "top"))
        baseline += len(out) * line_height + size * 0.3

    first_line = day.isoformat()
    if is_today and now_local is not None:
        first_line += f" {now_local.strftime('%H:%M:%S')}"
    day_length = (
        _format_duration((sunset_at - sunrise_at).total_seconds()) if sunrise_at is not None and sunset_at is not None else "--"
    )
    if show_now:
        elevation = float(current_elevation_deg) if current_elevation_deg is not None else 0.0
        sun_line = (
            f"Sun: Az{_NBSP}{float(current_azimuth_deg):.1f}°{_DOT} El{_NBSP}{_signed(elevation)}°{_DOT} "
            f"Len{_NBSP}{day_length}"
        )
    else:
        sun_line = f"Sun: Len{_NBSP}{day_length}"
    block([first_line, sun_line], readout_size, _READOUT_COLOR)

    if moon_fraction is not None:
        phase = f"{moon_phase_name(moon_fraction, bool(moon_waxing))} {round(moon_fraction * 100)}%"
        if is_today and moon_azimuth_deg is not None and moon_elevation_deg is not None:
            moon_line = (
                f"Moon: Az{_NBSP}{float(moon_azimuth_deg):.1f}°{_DOT} "
                f"El{_NBSP}{_signed(float(moon_elevation_deg))}°{_DOT} {phase}"
            )
        else:
            moon_line = f"Moon: {phase}"
        block([moon_line], moon_text_size, _MOON_TEXT_COLOR)

    parts.extend(labels)
    parts.append("</svg>")
    return "".join(parts)
