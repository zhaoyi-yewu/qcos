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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""
Export QCOS database in multiple formats.

Supported formats:
    sql  - full logical dump via pg_dump (schema + data)
    csv  - each table exported as an independent .csv file into a directory
    json - all tables aggregated into a single .json file
    toml - all tables aggregated into a single .toml file

Prerequisite:
    - sql:  PostgreSQL client tools (pg_dump) in PATH
    - csv/json/toml: SQLAlchemy + pg8000 driver installed
    - toml: tomli_w or tomlkit installed

Examples:
    # default sql dump
    ./export-database.py
    docker exec postgres pg_dump --host 127.0.0.1 --username qcos --dbname qcos --file /var/qcos/backup/database/qcos-database.sql

    # export as json
    ./export-database.py -t json -o ./qcos-database.json

    # export as csv (directory will be created)
    ./export-database.py -t csv -o ./qcos-database.csv

    # export as toml with custom credentials
    ./export-database.py -t toml -o ./qcos-database.toml --db-name qcos --db-url 127.0.0.1:5432 --username admin --password s3cret
"""

import csv
import json
import os
import shutil
import subprocess
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

# optional third-party dependencies (required only for non-sql formats)
try:
    from sqlalchemy import create_engine, inspect, text
except ImportError:  # pragma: no cover
    create_engine = None
    inspect = None
    text = None

try:
    import tomli_w
except ImportError:  # pragma: no cover
    tomli_w = None

try:
    import tomlkit
except ImportError:  # pragma: no cover
    tomlkit = None


# default connection parameters
DEFAULT_DB_NAME = "qcos"
DEFAULT_DB_URL = "127.0.0.1:5432"
DEFAULT_USERNAME = "qcos"
DEFAULT_PASSWORD = ""
DEFAULT_FILE_TYPE = "sql"

SUPPORTED_FILE_TYPES = ("sql", "csv", "json", "toml")

# password may be provided via environment variable
PASSWORD_ENV = "QCOS_DATABASE_PASSWORD"


def parse_db_url(db_url):
    """Parse ``host:port`` style url into (host, port).

    If port is omitted, default postgresql port 5432 is used.
    """
    if not db_url:
        raise ValueError("db_url must not be empty")

    # strip scheme if user passed a full jdbc-like url
    if "://" in db_url:
        db_url = db_url.split("://", 1)[1]

    # strip credentials if present (user:pass@host:port)
    if "@" in db_url:
        db_url = db_url.rsplit("@", 1)[1]

    # strip leading slash
    db_url = db_url.lstrip("/")

    if ":" in db_url:
        host, port = db_url.rsplit(":", 1)
        try:
            port = int(port)
        except ValueError as exc:
            raise ValueError(f"invalid port in db_url: {db_url}") from exc
    else:
        host = db_url
        port = 5432

    if not host:
        raise ValueError(f"invalid host in db_url: {db_url}")

    return host, port


def build_connection_url(host, port, username, password, db_name):
    """Build a SQLAlchemy connection URL for postgresql+psycopg."""
    if password:
        auth = f"{username}:{quote_plus(password)}"
    else:
        auth = username
    return f"postgresql+psycopg://{auth}@{host}:{port}/{db_name}"


def build_output_path(output, db_name, file_type):
    """Resolve output path according to file type.

    - csv: a directory (one csv file per table)
    - sql/json/toml: a single file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if file_type == "csv":
        if output:
            return Path(output)
        return Path.cwd() / f"{db_name}_{timestamp}_csv"

    if output:
        return Path(output)

    return Path.cwd() / f"{db_name}_{timestamp}.{file_type}"


def to_native(value):
    """Convert a DB cell value to a native python type suitable for
    json/toml/csv serialization."""
    if value is None:
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def run_pg_dump(db_name, host, port, username, password, output_path,
                schema_only=False, data_only=False):
    """Execute pg_dump and write result to output_path."""
    # pass password via PGPASSWORD env var (avoid leaking on cmdline)
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    cmd = [
        "pg_dump",
        "--host", str(host),
        "--port", str(port),
        "--username", username,
        "--dbname", db_name,
        "--file", str(output_path),
        "--no-password",
    ]

    if schema_only:
        cmd.append("--schema-only")
    if data_only:
        cmd.append("--data-only")

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("ERROR: pg_dump not found. Please install PostgreSQL client "
              "tools and ensure pg_dump is in PATH.",
              file=sys.stderr)
        return 1

    if result.returncode != 0:
        print(f"ERROR: pg_dump failed with code {result.returncode}",
              file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode

    if result.stderr:
        # pg_dump writes progress/warnings to stderr
        print(result.stderr, file=sys.stderr)

    return 0


def export_csv(engine, output_dir):
    """Export every table as an independent csv file into output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if not table_names:
        print("WARNING: no tables found in database", file=sys.stderr)
        return 0

    with engine.connect() as conn:
        for table in table_names:
            stmt = text(f'SELECT * FROM "{table}"')
            result = conn.execute(stmt)
            columns = list(result.keys())
            csv_path = output_dir / f"{table}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(columns)
                for row in result:
                    writer.writerow(
                        ["" if v is None else to_native(v) for v in row]
                    )
            print(f"  exported table: {table} -> {csv_path}")

    return 0


def export_json(engine, output_path):
    """Export all tables into a single json file."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    data = {}

    if not table_names:
        print("WARNING: no tables found in database", file=sys.stderr)

    with engine.connect() as conn:
        for table in table_names:
            stmt = text(f'SELECT * FROM "{table}"')
            result = conn.execute(stmt)
            columns = list(result.keys())
            rows = []
            for row in result:
                rows.append({
                    col: to_native(val)
                    for col, val in zip(columns, row)
                })
            data[table] = rows
            print(f"  loaded table: {table} ({len(rows)} rows)")

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)

    return 0


def export_toml(engine, output_path):
    """Export all tables into a single toml file."""
    # prefer tomli_w, fallback to tomlkit
    if tomli_w is None and tomlkit is None:
        print("ERROR: neither tomli_w nor tomlkit is installed. "
              "Install one of them: pip install tomli_w  (or tomlkit)",
              file=sys.stderr)
        return 1

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    data = {}

    if not table_names:
        print("WARNING: no tables found in database", file=sys.stderr)

    with engine.connect() as conn:
        for table in table_names:
            stmt = text(f'SELECT * FROM "{table}"')
            result = conn.execute(stmt)
            columns = list(result.keys())
            rows = []
            for row in result:
                # toml does not support None; use empty string instead
                rows.append({
                    col: ("" if val is None else to_native(val))
                    for col, val in zip(columns, row)
                })
            data[table] = rows
            print(f"  loaded table: {table} ({len(rows)} rows)")

    if tomli_w is not None:
        with open(output_path, "wb") as fh:
            tomli_w.dump(data, fh)
    else:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(tomlkit.dumps(data))

    return 0


def run_sqlalchemy_export(file_type, db_name, host, port, username,
                          password, output_path):
    """Connect to database via SQLAlchemy and export data."""
    if create_engine is None:
        print("ERROR: SQLAlchemy is not installed. "
              "Install it with: pip install sqlalchemy pg8000",
              file=sys.stderr)
        return 1

    conn_url = build_connection_url(host, port, username, password, db_name)
    try:
        engine = create_engine(conn_url)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to create engine: {exc}", file=sys.stderr)
        return 1

    try:
        if file_type == "csv":
            return export_csv(engine, output_path)
        if file_type == "json":
            return export_json(engine, output_path)
        if file_type == "toml":
            return export_toml(engine, output_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: export failed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    print(f"ERROR: unsupported file type: {file_type}", file=sys.stderr)
    return 1


def main(argv=None):
    """main"""
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip()
    program_license = f'''{program_shortdesc}

USAGE
'''

    parser = ArgumentParser(
        description=program_license,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument("-n", "--db-name", dest="db_name",
                        default=DEFAULT_DB_NAME,
                        help=f"database name (default: {DEFAULT_DB_NAME})")
    parser.add_argument("-u", "--db-url", dest="db_url",
                        default=DEFAULT_DB_URL,
                        help=f"database url as host:port "
                             f"(default: {DEFAULT_DB_URL})")
    parser.add_argument("-U", "--username", dest="username",
                        default=DEFAULT_USERNAME,
                        help=f"database username "
                             f"(default: {DEFAULT_USERNAME})")
    parser.add_argument("-p", "--password", dest="password",
                        default=os.environ.get(PASSWORD_ENV, DEFAULT_PASSWORD),
                        help=f"database password "
                             f"(default: env {PASSWORD_ENV} or empty)")
    parser.add_argument("-t", "--file-type", dest="file_type",
                        choices=SUPPORTED_FILE_TYPES,
                        default=DEFAULT_FILE_TYPE,
                        help=f"output file type (default: {DEFAULT_FILE_TYPE}; "
                             "csv exports a directory, one file per table)")
    parser.add_argument("-o", "--output", dest="output",
                        default=None,
                        help="output path: file for sql/json/toml, "
                             "directory for csv "
                             "(default: <db_name>_<timestamp>.<ext> in cwd)")
    export_group = parser.add_mutually_exclusive_group()
    export_group.add_argument("--schema-only", dest="schema_only",
                              action="store_true",
                              help="dump schema only, no data (sql only)")
    export_group.add_argument("--data-only", dest="data_only",
                              action="store_true",
                              help="dump data only, no schema (sql only)")

    args = parser.parse_args()

    # resolve parameters
    db_name = args.db_name
    username = args.username
    password = args.password
    file_type = args.file_type

    try:
        host, port = parse_db_url(args.db_url)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output_path = build_output_path(args.output, db_name, file_type)

    print(f"Exporting database: {db_name}")
    print(f"  host      : {host}")
    print(f"  port      : {port}")
    print(f"  username  : {username}")
    print(f"  file type : {file_type}")
    print(f"  output    : {output_path}")

    if file_type == "sql":
        # sql mode uses pg_dump
        if shutil.which("pg_dump") is None:
            print("ERROR: pg_dump not found in PATH. Please install "
                  "PostgreSQL client tools first.",
                  file=sys.stderr)
            return 1

        print(f"  mode      : "
              f"{'schema-only' if args.schema_only else 'data-only' if args.data_only else 'full'}")

        rc = run_pg_dump(
            db_name=db_name,
            host=host,
            port=port,
            username=username,
            password=password,
            output_path=output_path,
            schema_only=args.schema_only,
            data_only=args.data_only,
        )
    else:
        # csv/json/toml mode uses SQLAlchemy
        rc = run_sqlalchemy_export(
            file_type=file_type,
            db_name=db_name,
            host=host,
            port=port,
            username=username,
            password=password,
            output_path=output_path,
        )

    if rc == 0:
        if file_type == "csv":
            file_count = len(list(output_path.glob("*.csv")))
            print(f"Export completed: {output_path} "
                  f"({file_count} csv files)")
        else:
            size = (output_path.stat().st_size
                    if output_path.exists() else 0)
            print(f"Export completed: {output_path} ({size} bytes)")
    else:
        print("Export failed.", file=sys.stderr)

    return rc


if __name__ == "__main__":
    sys.exit(main())
