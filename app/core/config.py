from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Real environment variables (e.g. set by ansible in production)
    # always take precedence over .env -- .env is a local-dev convenience
    # only, matching Django's own convention of reading from actual env
    # vars, not a .env file.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str

    owserver_url: str = "http://10.0.0.188/details.xml"

    dyson_host: str = "10.0.0.17"
    dyson_serial: str = ""
    dyson_credentials: str = ""
    dyson_product_type: str = ""
    dyson_name: str = ""
    dyson_version: str = ""

    # Almanac / house-compass panel. Defaults are Greenwich, matching
    # astral's own Observer defaults -- harmless placeholders, but the
    # compass and the logged sun times are meaningless until these are set
    # to the house's real coordinates.
    site_name: str = "home"
    latitude: Decimal = Decimal("51.4733")
    longitude: Decimal = Decimal("-0.0008333")
    elevation_m: Decimal = Decimal("0")
    timezone: str = "UTC"
    house_image_path: str = ""
    # Compass geometry, tuned against the actual house photo. Defaults
    # assume a north-up image with the house centred.
    compass_north_offset_deg: float = 0.0
    compass_center_x_pct: float = 0.5
    compass_center_y_pct: float = 0.5
    compass_radius_pct: float = 0.42

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
