from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class AlmanacDayLogRequest(BaseModel):
    day: date

    # --- Provenance -----------------------------------------------------
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    elevation_m: Decimal | None = None
    timezone_name: str | None = None
    raw: dict | None = None  # the whole API response, verbatim

    # march_equinox | june_solstice | september_equinox | december_solstice
    event: str | None = None

    # --- Sun times --------------------------------------------------------
    sunrise_at: datetime | None = None
    sunset_at: datetime | None = None
    solar_noon_at: datetime | None = None
    day_length_seconds: int | None = None
    sun_status: str | None = None

    # --- Twilight / golden & blue hour -------------------------------------
    morning_astronomical_twilight_begin_at: datetime | None = None
    morning_astronomical_twilight_end_at: datetime | None = None
    morning_nautical_twilight_begin_at: datetime | None = None
    morning_nautical_twilight_end_at: datetime | None = None
    morning_civil_twilight_begin_at: datetime | None = None
    morning_civil_twilight_end_at: datetime | None = None
    morning_blue_hour_begin_at: datetime | None = None
    morning_blue_hour_end_at: datetime | None = None
    morning_golden_hour_begin_at: datetime | None = None
    morning_golden_hour_end_at: datetime | None = None

    evening_golden_hour_begin_at: datetime | None = None
    evening_golden_hour_end_at: datetime | None = None
    evening_blue_hour_begin_at: datetime | None = None
    evening_blue_hour_end_at: datetime | None = None
    evening_civil_twilight_begin_at: datetime | None = None
    evening_civil_twilight_end_at: datetime | None = None
    evening_nautical_twilight_begin_at: datetime | None = None
    evening_nautical_twilight_end_at: datetime | None = None
    evening_astronomical_twilight_begin_at: datetime | None = None
    evening_astronomical_twilight_end_at: datetime | None = None

    night_begin_at: datetime | None = None
    mid_night_at: datetime | None = None
    night_end_at: datetime | None = None

    # --- Moon ---------------------------------------------------------------
    moon_phase: str | None = None
    moonrise_at: datetime | None = None
    moonset_at: datetime | None = None
    moon_altitude_deg: Decimal | None = None
    moon_azimuth_deg: Decimal | None = None
    moon_distance_km: Decimal | None = None
    moon_parallactic_angle_deg: Decimal | None = None
    moon_illumination_percentage: Decimal | None = None
    moon_angle_deg: Decimal | None = None
    moon_status: str | None = None

    # --- Position at the request instant (see AlmanacDay's docstring) -----
    api_observed_at: datetime | None = None
    sun_altitude_deg_at_observation: Decimal | None = None
    sun_azimuth_deg_at_observation: Decimal | None = None
    sun_distance_km: Decimal | None = None


class AlmanacDayLogResponse(BaseModel):
    site: str
    day: date
    created: bool  # False when skipped due to dedup (unchanged reading)
    # Echoed back so the logger can print them without recomputing locally.
    sunrise_azimuth_deg: Decimal | None
    sunset_azimuth_deg: Decimal | None
    moonrise_azimuth_deg: Decimal | None
    moonset_azimuth_deg: Decimal | None


class AlmanacDatesResponse(BaseModel):
    dates: list[date]
