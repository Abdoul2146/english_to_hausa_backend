import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
# 1. Add project root to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# 2. Import settings and declarative Base
from models.config import settings
from models.database import Base
# 3. Get logging configuration
config = context.config
# 4. Set the PostgreSQL connection string dynamically from our centralized settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
# 5. Set target metadata for automatic schema detection
target_metadata = Base.metadata
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()