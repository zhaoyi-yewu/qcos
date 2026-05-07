#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.engine.url import make_url

try:
    import tomllib
except ImportError:
    import tomli as tomllib

top_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(top_dir))
from wy_qcos.db.models import Base  # noqa: E402

# QCOS config file
qcos_config_file = "/etc/qcos/qcos.toml"

# Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# for 'autogenerate' support, add model MetaData object here
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url_from_config()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = get_url_from_config()

    cfg = {"sqlalchemy.url": url}
    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def get_url_from_config():
    """Get database url from env or config file."""
    db_str = "QCOS_DATABASE_CONNECTION_URL"

    # 1. Try to get from environment variable first
    print(f"[1/3] Attempting to read {db_str} from environment variable")
    db_connection_url = os.environ.get(db_str, None)
    if db_connection_url:
        print(f"✓ Found {db_str} in environment variable")
        url = make_url(db_connection_url)
        if not database_exists(url):
            create_database(url)
            print(f"✓ Database '{url.database}' created.")
        return url

    # 2. Try to get from TOML config file
    print(f"[2/3] Attempting to read {db_str} from config file: {qcos_config_file}")
    if os.path.exists(qcos_config_file):
        try:
            with open(qcos_config_file, "rb") as f:
                config_data = tomllib.load(f)

            # Navigate through the config hierarchy
            # Expected path: config_data['DATABASE']['QCOS_DATABASE_CONNECTION_URL']
            if "DATABASE" in config_data and db_str in config_data["DATABASE"]:
                db_connection_url = config_data["DATABASE"][db_str]
                if db_connection_url:
                    print(f"✓ Found {db_str} in config file")
                    url = make_url(db_connection_url)
                    if not database_exists(url):
                        create_database(url)
                        print(f"✓ Database '{url.database}' created.")
                    return url
        except Exception as e:
            print(f"✗ Error reading config file: {e}")
    else:
        print(f"✗ Config file not found: {qcos_config_file}")

    # 3. If still not found, raise error
    print(f"[3/3] ERROR: Could not find {db_str}")
    raise Exception(
        f"Could not find '{db_str}'. Please:\n"
        f"  1. Set environment variable: export {db_str}='postgresql://...'\n"
        f"  2. Or configure it in {qcos_config_file} under [DATABASE] section\n"
        f"     Example: {db_str} = 'postgresql://user:password@localhost:5432/qcos'"
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
