from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import DateTime as SADateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AlmanacDay(SQLModel, table=True):
    """One row per (site, day) -- genuinely one-row-per-day data, unlike
    every other table here, which is either a dimension row or a
    timestamped log row. Follows EnergyCircuit's precedent for a
    composite-uniqueness dimension table: surrogate `id` PK plus a
    UniqueConstraint, upserted by the router via select-then-mutate.

    `site` exists so a second location (e.g. a cabin) can be logged later
    without a schema change -- not used for anything yet.

    api.ipgeolocation.io's /v3/astronomy has no `time` parameter, only
    `date` -- its `sun_altitude`/`sun_azimuth`/`moon_altitude`/
    `moon_azimuth` fields are the position *at the instant of the
    request* (it returns `current_time` alongside them), not at any
    point during the requested day. The `..._at_observation` columns
    below are named to make that honest; they are NOT "today's" azimuth
    at any meaningful moment unless the request happened to be made on
    that same day. The actually-useful rise/set azimuths
    (`sunrise_azimuth_deg` etc.) are computed locally in
    app/services/almanac.py with astral, not read from the API.
    """

    __tablename__ = "almanac_days"
    __table_args__ = (UniqueConstraint("site", "day"),)

    id: int | None = Field(default=None, primary_key=True)
    site: str = Field(max_length=50, index=True)
    day: date = Field(index=True)

    # --- Provenance -----------------------------------------------------
    latitude: Decimal | None = Field(default=None, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, max_digits=9, decimal_places=6)
    elevation_m: Decimal | None = Field(default=None, max_digits=7, decimal_places=2)
    timezone_name: str | None = Field(default=None, max_length=64)
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False, index=True),
    )
    # The whole API response, verbatim -- so a new upstream field is never
    # lost even though only a subset is broken out into its own column.
    raw: dict | None = Field(default=None, sa_column=Column(JSONB))

    # march_equinox | june_solstice | september_equinox | december_solstice,
    # else NULL for an ordinary logged day (today, today+7, today+30).
    event: str | None = Field(default=None, max_length=30, index=True)

    # --- Sun times --------------------------------------------------------
    sunrise_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    sunset_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    solar_noon_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    day_length_seconds: int | None = Field(default=None)
    sun_status: str | None = Field(default=None, max_length=50)

    # --- Twilight / golden & blue hour (API's morning/evening, flattened) -
    morning_astronomical_twilight_begin_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    morning_astronomical_twilight_end_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    morning_nautical_twilight_begin_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    morning_nautical_twilight_end_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    morning_civil_twilight_begin_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    morning_civil_twilight_end_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    morning_blue_hour_begin_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    morning_blue_hour_end_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    morning_golden_hour_begin_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    morning_golden_hour_end_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))

    evening_golden_hour_begin_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    evening_golden_hour_end_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    evening_blue_hour_begin_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    evening_blue_hour_end_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    evening_civil_twilight_begin_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    evening_civil_twilight_end_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    evening_nautical_twilight_begin_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    evening_nautical_twilight_end_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    evening_astronomical_twilight_begin_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    evening_astronomical_twilight_end_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )

    night_begin_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    mid_night_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    night_end_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))

    # --- Moon -------------------------------------------------------------
    moon_phase: str | None = Field(default=None, max_length=20)
    moonrise_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    moonset_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    moon_altitude_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    moon_azimuth_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    moon_distance_km: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    moon_parallactic_angle_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    # Signed string in the API ("-84.72" while waning) -- kept as Decimal,
    # sign and all, rather than splitting into a separate waxing/waning flag.
    moon_illumination_percentage: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    moon_angle_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    moon_status: str | None = Field(default=None, max_length=50)

    # --- Position at the request instant, NOT "this day's" position ------
    # See the class docstring. Useful for knowing when the row was fetched
    # relative to the sun, not for anything about the stored `day` itself.
    api_observed_at: datetime | None = Field(default=None, sa_column=Column(SADateTime(timezone=True)))
    sun_altitude_deg_at_observation: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    sun_azimuth_deg_at_observation: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    sun_distance_km: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)

    # --- Derived locally (astral), not from the API ------------------------
    sunrise_azimuth_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    sunset_azimuth_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    moonrise_azimuth_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    moonset_azimuth_deg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)


# Fields that participate in dedup/change comparison -- same convention as
# SPA_LOG_METRIC_FIELDS/HVAC_ZONE_LOG_METRIC_FIELDS. Excludes identity
# (id/site/day), bookkeeping (fetched_at, raw), and the derived azimuth
# columns, which are recomputed every time from sunrise_at/sunset_at/
# moonrise_at/moonset_at and so are implied by them, not independent facts.
ALMANAC_METRIC_FIELDS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "elevation_m",
    "timezone_name",
    "event",
    "sunrise_at",
    "sunset_at",
    "solar_noon_at",
    "day_length_seconds",
    "sun_status",
    "morning_astronomical_twilight_begin_at",
    "morning_astronomical_twilight_end_at",
    "morning_nautical_twilight_begin_at",
    "morning_nautical_twilight_end_at",
    "morning_civil_twilight_begin_at",
    "morning_civil_twilight_end_at",
    "morning_blue_hour_begin_at",
    "morning_blue_hour_end_at",
    "morning_golden_hour_begin_at",
    "morning_golden_hour_end_at",
    "evening_golden_hour_begin_at",
    "evening_golden_hour_end_at",
    "evening_blue_hour_begin_at",
    "evening_blue_hour_end_at",
    "evening_civil_twilight_begin_at",
    "evening_civil_twilight_end_at",
    "evening_nautical_twilight_begin_at",
    "evening_nautical_twilight_end_at",
    "evening_astronomical_twilight_begin_at",
    "evening_astronomical_twilight_end_at",
    "night_begin_at",
    "mid_night_at",
    "night_end_at",
    "moon_phase",
    "moonrise_at",
    "moonset_at",
    "moon_altitude_deg",
    "moon_azimuth_deg",
    "moon_distance_km",
    "moon_parallactic_angle_deg",
    "moon_illumination_percentage",
    "moon_angle_deg",
    "moon_status",
    "api_observed_at",
    "sun_altitude_deg_at_observation",
    "sun_azimuth_deg_at_observation",
    "sun_distance_km",
    "sunrise_azimuth_deg",
    "sunset_azimuth_deg",
    "moonrise_azimuth_deg",
    "moonset_azimuth_deg",
)
