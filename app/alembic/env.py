from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

import app.models  # noqa: F401  -- registers all tables on SQLModel.metadata
from app.core.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read DATABASE_URL from the same env-var-driven settings the app uses,
# rather than a hardcoded value in alembic.ini. Alembic's Config is
# backed by a ConfigParser, which treats "%" as the start of an
# interpolation sequence (e.g. "%(foo)s") even for values set
# programmatically via set_main_option -- a URL-encoded password
# (containing e.g. "%24" for "$") would otherwise raise
# "invalid interpolation syntax". Escape "%" as "%%" so ConfigParser
# stores/reads it literally.
database_url = get_settings().sqlalchemy_database_url
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    # The `api` database is shared with Django features this migration
    # deliberately doesn't manage (admin, social auth, referrals,
    # avatars, django's own sessions/contenttypes/auth tables, and a
    # handful of unexplained scratch tables like del_max/del_min).
    # Without this filter, `alembic check`/autogenerate treats every
    # such table as "should be removed" simply because it isn't in our
    # SQLModel.metadata. Only ever consider tables we've explicitly
    # modeled -- everything else on the reflected (live) side is
    # invisible to comparison, and we never emit DDL for it.
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
