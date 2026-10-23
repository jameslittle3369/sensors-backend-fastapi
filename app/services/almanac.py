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
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from html import escape
from math import cos, radians, sin
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
    return _round2(fn(observer, at))


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

_SUNRISE_COLOR = "#f5a623"  # warm gold
_SUNSET_COLOR = "#c0392b"  # deep orange-red
_CURRENT_SUN_COLOR = "#ffd54a"  # bright yellow
_SWEPT_ARC_COLOR = "#ffd54a"
_REMAINING_ARC_COLOR = "#f5a623"
_RING_COLOR = "#ffffff"


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
) -> str:
    """The whole panel image: the house photo at its native resolution,
    with a compass ring, sunrise/sunset rays, and (when `is_today`) the
    current sun bearing and the arcs swept from sunrise to now and from
    now to sunset. When not `is_today`, a single arc spans sunrise to
    sunset instead -- there is no "now" to split it at."""
    mime, width, height = sniff_image(image_bytes)
    data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"

    cx = width * center_x_pct
    cy = height * center_y_pct
    r = min(width, height) * radius_pct

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">',
        f'<image x="0" y="0" width="{width}" height="{height}" href="{data_uri}" />',
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="none" '
        f'stroke="{_RING_COLOR}" stroke-width="2" stroke-opacity="0.85" />',
    ]

    # Tick marks every 30 degrees, cardinal points labelled.
    for tick_deg, label in (
        (0, "N"),
        (30, None),
        (60, None),
        (90, "E"),
        (120, None),
        (150, None),
        (180, "S"),
        (210, None),
        (240, None),
        (270, "W"),
        (300, None),
        (330, None),
    ):
        inner = r * 0.92
        outer = r * 1.0
        x1, y1 = _point(cx, cy, inner, tick_deg, north_offset_deg)
        x2, y2 = _point(cx, cy, outer, tick_deg, north_offset_deg)
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{_RING_COLOR}" stroke-width="2" stroke-opacity="0.85" />'
        )
        if label:
            lx, ly = _point(cx, cy, r * 1.12, tick_deg, north_offset_deg)
            parts.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" fill="{_RING_COLOR}" font-size="{r * 0.09:.1f}" '
                f'font-weight="bold" text-anchor="middle" dominant-baseline="middle" '
                f'style="paint-order: stroke; stroke: #000; stroke-width: 3px; stroke-opacity: 0.6;">'
                f"{label}</text>"
            )

    # Sunrise / sunset rays, with a time + bearing label at the ring edge.
    for azimuth, color, caption, when in (
        (sunrise_azimuth_deg, _SUNRISE_COLOR, "Sunrise", sunrise_at),
        (sunset_azimuth_deg, _SUNSET_COLOR, "Sunset", sunset_at),
    ):
        if azimuth is None:
            continue
        az = float(azimuth)
        x, y = _point(cx, cy, r, az, north_offset_deg)
        parts.append(
            f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{x:.2f}" y2="{y:.2f}" '
            f'stroke="{color}" stroke-width="3" stroke-opacity="0.9" />'
        )
        lx, ly = _point(cx, cy, r * 1.22, az, north_offset_deg)
        parts.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" fill="{color}" font-size="{r * 0.075:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'style="paint-order: stroke; stroke: #000; stroke-width: 3px; stroke-opacity: 0.6;">'
            f"{escape(caption)} {_format_local_time(when)} ({az:05.1f}°)</text>"
        )

    # Arcs + current sun position.
    if is_today and current_azimuth_deg is not None and sunrise_azimuth_deg is not None and sunset_azimuth_deg is not None:
        cur = float(current_azimuth_deg)
        swept = _arc_path(cx, cy, r, float(sunrise_azimuth_deg), cur, north_offset_deg)
        remaining = _arc_path(cx, cy, r, cur, float(sunset_azimuth_deg), north_offset_deg)
        if swept:
            parts.append(
                f'<path d="{swept}" fill="none" stroke="{_SWEPT_ARC_COLOR}" '
                f'stroke-width="5" stroke-opacity="0.9" />'
            )
        if remaining:
            parts.append(
                f'<path d="{remaining}" fill="none" stroke="{_REMAINING_ARC_COLOR}" '
                f'stroke-width="3" stroke-opacity="0.35" stroke-dasharray="6,6" />'
            )
        elevation = float(current_elevation_deg) if current_elevation_deg is not None else 0.0
        sun_r = r * cos(radians(elevation))
        sx, sy = _point(cx, cy, sun_r, cur, north_offset_deg)
        parts.append(
            f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{r * 0.06:.2f}" fill="{_CURRENT_SUN_COLOR}" '
            f'stroke="#000" stroke-width="1.5" stroke-opacity="0.5" />'
        )
        readout = f"Sun: {cur:05.1f}°, elevation {elevation:+.1f}°"
    elif sunrise_azimuth_deg is not None and sunset_azimuth_deg is not None:
        full_day = _arc_path(cx, cy, r, float(sunrise_azimuth_deg), float(sunset_azimuth_deg), north_offset_deg)
        if full_day:
            parts.append(
                f'<path d="{full_day}" fill="none" stroke="{_SWEPT_ARC_COLOR}" '
                f'stroke-width="4" stroke-opacity="0.55" />'
            )
        readout = "Not today -- showing the full daytime arc"
    else:
        readout = "Sun does not rise or set on this day"

    parts.append(
        f'<text x="{width * 0.02:.1f}" y="{height * 0.05:.1f}" fill="{_RING_COLOR}" font-size="{r * 0.09:.1f}" '
        f'style="paint-order: stroke; stroke: #000; stroke-width: 3px; stroke-opacity: 0.6;">'
        f"{escape(day.isoformat())} — {escape(readout)}</text>"
    )

    parts.append("</svg>")
    return "".join(parts)
