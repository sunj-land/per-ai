import sys
import os
from logging.config import fileConfig

from sqlmodel import SQLModel

from alembic import context

# Ensure backend/ is on sys.path so app.* imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import engine (already configured with WAL pragma and correct DB path)
from app.core.database import engine  # noqa: E402

# Import all models so SQLModel.metadata is fully populated
import app.models.agent_store  # noqa: F401, E402
import app.models.attachment  # noqa: F401
import app.models.card  # noqa: F401
import app.models.channel  # noqa: F401
import app.models.chat  # noqa: F401
import app.models.content  # noqa: F401
import app.models.note  # noqa: F401
import app.models.plan  # noqa: F401
import app.models.progress  # noqa: F401
import app.models.reminder  # noqa: F401
import app.models.rss  # noqa: F401
import app.models.rss_quality  # noqa: F401
import app.models.schedule  # noqa: F401
import app.models.task  # noqa: F401
import app.models.user  # noqa: F401
import app.models.user_profile  # noqa: F401

# Alembic Config object (gives access to .ini values)
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use SQLModel's shared metadata as the migration target
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite column changes
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    # Reuse the app's engine so WAL mode and connect_args are applied
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite column changes
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
