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
# pylint: disable=bad-continuation

"""Security-focused unit tests for standalone scripts."""

import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

TOP_DIR = Path(__file__).resolve().parents[4]


def load_script(relative_path, module_name):
    """Load a standalone script without executing its CLI entry point."""
    script_path = TOP_DIR / relative_path
    spec = spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@patch.object(Path, "rglob", return_value=iter(()))
@patch.object(Path, "glob", return_value=iter(()))
@patch("setuptools.setup")
def test_cmake_parallel_jobs_are_validated(
    mock_setup, mock_glob, mock_rglob, monkeypatch
):
    """Test CMake parallel jobs are validated against malicious input."""
    root_setup = load_script("setup.py", "security_root_setup")
    standalone_setup = load_script(
        "src_cpp/packages/wy_transpiler/setup.py",
        "security_standalone_setup",
    )

    default_jobs = getattr(os, "cpu_count")() or 1
    for module in (root_setup, standalone_setup):
        for value in ("2;id", "-1", "0", "１２"):
            monkeypatch.setenv("CMAKE_BUILD_PARALLEL_LEVEL", value)
            assert module.CMakeBuildExt._parallel_jobs() == default_jobs
        monkeypatch.setenv("CMAKE_BUILD_PARALLEL_LEVEL", "8")
        assert module.CMakeBuildExt._parallel_jobs() == 8
        monkeypatch.setenv("CMAKE_BUILD_PARALLEL_LEVEL", "9999")
        assert module.CMakeBuildExt._parallel_jobs() == 256


def test_database_output_path_is_confined(tmp_path, monkeypatch):
    """Test database output path is confined to the working directory."""
    module = load_script(
        "bin/export-database.py", "security_export_database_paths"
    )
    monkeypatch.chdir(tmp_path)

    output = module.build_output_path("exports/qcos.sql", "qcos", "sql")
    assert output == (tmp_path / "exports/qcos.sql").resolve()
    with pytest.raises(ValueError, match="output path must be within"):
        module.build_output_path("../qcos.sql", "qcos", "sql")


def test_pg_dump_rejects_invalid_database_name(monkeypatch, tmp_path):
    """Test pg_dump rejects invalid database names."""
    module = load_script(
        "bin/export-database.py", "security_export_database_command"
    )
    run_mock = Mock()
    find_mock = Mock()
    monkeypatch.setattr(module.subprocess, "run", run_mock)
    monkeypatch.setattr(module, "find_pg_dump", find_mock)

    result = module.run_pg_dump(
        "qcos;id",
        "127.0.0.1",
        5432,
        "qcos",
        None,
        tmp_path / "qcos.sql",
    )

    assert result == 1
    find_mock.assert_not_called()
    run_mock.assert_not_called()


def test_pg_dump_uses_validated_executable_and_clean_env(
    monkeypatch, tmp_path
):
    """Test pg_dump uses validated executable and clean environment."""
    module = load_script(
        "bin/export-database.py", "security_export_database_executable"
    )
    executable_name = "pg_dump.exe" if module.os.name == "nt" else "pg_dump"
    executable = tmp_path / "bin" / executable_name
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    executable.chmod(0o755)
    run_mock = Mock(return_value=SimpleNamespace(returncode=0, stderr=""))
    monkeypatch.setattr(module, "PG_DUMP_SEARCH_DIRS", (executable.parent,))
    monkeypatch.setattr(module, "PG_DUMP_VERSIONED_DIRS", ())
    monkeypatch.setattr(module.subprocess, "run", run_mock)
    monkeypatch.setenv("PATH", str(tmp_path / "malicious"))
    monkeypatch.setenv("PGOPTIONS", "malicious")

    output_path = tmp_path / "exports with spaces" / "qcos database.sql"
    result = module.run_pg_dump(
        "qcos",
        "127.0.0.1",
        5432,
        "qcos",
        None,
        output_path,
    )

    assert result == 0
    command = run_mock.call_args.args[0]
    assert Path(command[0]).is_absolute()
    assert command[command.index("--dbname") + 1] == "qcos"
    assert command[command.index("--file") + 1] == str(output_path)
    assert run_mock.call_args.kwargs["shell"] is False
    assert run_mock.call_args.kwargs["env"] == {}


def test_pg_dump_ignores_untrusted_path(monkeypatch, tmp_path):
    """Test pg_dump ignores untrusted PATH entries."""
    module = load_script(
        "bin/export-database.py", "security_export_database_untrusted_path"
    )
    executable_name = "pg_dump.exe" if module.os.name == "nt" else "pg_dump"
    malicious = tmp_path / "malicious" / executable_name
    malicious.parent.mkdir(parents=True)
    malicious.write_text("", encoding="utf-8")
    malicious.chmod(0o755)
    run_mock = Mock()
    monkeypatch.setenv("PATH", str(malicious.parent))
    monkeypatch.setattr(module, "PG_DUMP_SEARCH_DIRS", ())
    monkeypatch.setattr(module, "PG_DUMP_VERSIONED_DIRS", ())
    monkeypatch.setattr(module.subprocess, "run", run_mock)

    result = module.run_pg_dump(
        "qcos",
        "127.0.0.1",
        5432,
        "qcos",
        None,
        tmp_path / "qcos.sql",
    )

    assert result == 1
    run_mock.assert_not_called()


@pytest.mark.parametrize(
    "relative_path",
    [
        "build-scripts/webui/parse-webui-toml.py",
        "requirements/install-venvs.py",
        "requirements/export-requirements.py",
    ],
)
def test_script_path_validators(relative_path, tmp_path):
    """Test script path validators reject traversal."""
    module = load_script(relative_path, "security_path_validator")
    root = tmp_path / "allowed"

    resolved = module.resolve_path_within("nested/output.txt", root)
    assert resolved == (root / "nested/output.txt").resolve()
    with pytest.raises(ValueError, match="path must be within"):
        module.resolve_path_within("../outside.txt", root)
    with pytest.raises(ValueError, match="path must be within"):
        module.resolve_path_within(tmp_path / "outside.txt", root)


def test_webui_main_writes_to_allowed_roots(tmp_path, monkeypatch):
    """Test webui main writes only to allowed roots."""
    module = load_script(
        "build-scripts/webui/parse-webui-toml.py", "security_webui_main"
    )
    config_dir = tmp_path / "config"
    json_dir = tmp_path / "apps"
    nginx_dir = tmp_path / "nginx"
    config_dir.mkdir()
    config_path = config_dir / "qcos-webui.toml"
    config_path.write_text(
        "[DEFAULT]\nQCOS_API_ENDPOINTS = []\n", encoding="utf-8"
    )
    monkeypatch.setattr(module, "TOML_ROOT", config_dir)
    monkeypatch.setattr(module, "ENV_OUTPUT_ROOT", config_dir)
    monkeypatch.setattr(module, "JSON_OUTPUT_ROOT", json_dir)
    monkeypatch.setattr(module, "NGINX_OUTPUT_ROOT", nginx_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "parse-webui-toml.py",
            "--toml",
            str(config_path),
            "--env-out",
            str(config_dir / "webui.env"),
            "--json-out",
            str(json_dir / "webui-config.json"),
            "--nginx-snippet-out",
            str(nginx_dir / "endpoints.conf"),
        ],
    )

    module.main()

    assert (config_dir / "webui.env").is_file()
    assert (json_dir / "webui-config.json").is_file()
    assert (nginx_dir / "endpoints.conf").is_file()


def test_install_venvs_main_resolves_allowed_paths(tmp_path, monkeypatch):
    """Test install-venvs main resolves allowed paths."""
    module = load_script(
        "requirements/install-venvs.py", "security_install_venvs_main"
    )
    project_dir = tmp_path / "project"
    venv_dir = tmp_path / "venv"
    config_path = project_dir / "requirements/venv-configs.toml"
    load_mock = Mock(return_value={})
    install_mock = Mock(return_value=0)
    monkeypatch.setattr(module, "TOP_DIR", project_dir)
    monkeypatch.setattr(module, "DEFAULT_VENV_BASE_DIR", venv_dir)
    monkeypatch.setattr(module, "load_driver_env_file", load_mock)
    monkeypatch.setattr(module, "install_venv", install_mock)
    monkeypatch.setattr(sys, "argv", ["install-venvs.py"])

    result = module.main([
        "--file",
        str(config_path),
        "--venv-dir",
        str(venv_dir),
        "--dry-run",
    ])

    assert result == 0
    assert load_mock.call_args.args[0] == config_path.resolve()
    assert install_mock.call_args.args[1] == venv_dir.resolve()


def test_export_requirements_main_confines_paths(tmp_path, monkeypatch):
    """Test export-requirements main confines paths."""
    module = load_script(
        "requirements/export-requirements.py", "security_export_reqs_main"
    )
    monkeypatch.setattr(module, "TOP_DIR", tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    output = tmp_path / "requirements.txt"
    pyproject.write_text(
        '[project]\ndependencies = ["tomlkit"]\n', encoding="utf-8"
    )

    result = module.main([str(pyproject), str(output)])

    assert result == 0
    assert output.read_text(encoding="utf-8") == "tomlkit\n"
    rejected = module.main([str(pyproject), "../outside.txt"])
    assert rejected == 2


def test_release_notes_remain_single_argument(monkeypatch):
    """Test release notes remain a single argument."""
    module = load_script(
        "cicd/release-version.py", "security_release_version_argv"
    )
    run_mock = Mock()
    monkeypatch.setattr(module, "run_command", run_mock)
    release_notes = 'Fix "quoted"\n--allow-dirty\n{value}'

    module.bump_version(None, "1.2.3", release_notes)

    command = run_mock.call_args.args[0]
    assert command == [
        "bump-my-version",
        "bump",
        "--commit",
        "--new-version",
        "1.2.3",
        "--tag-message",
        'Release Notes\n\nFix "quoted"\n--allow-dirty\n{{value}}',
    ]
    assert "--allow-dirty" not in command[:-1]
    assert run_mock.call_args.kwargs == {"cwd": "."}
