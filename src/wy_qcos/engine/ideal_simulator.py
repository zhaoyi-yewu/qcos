#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# ----------------------------------------------------------------------

"""Run ideal simulation in the Qiskit Aer driver's environment."""

import asyncio
import json
import locale
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

IDEAL_SIMULATOR_NAME = "qiskit_aer_sim"
IDEAL_SIMULATOR_TIMEOUT = 120
QISKIT_AER_DRIVER_NAME = "DriverQiskitAerSim"


def _run_command(command, environment):
    """Execute an isolated process without invoking a command shell."""

    async def execute():
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=environment,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=IDEAL_SIMULATOR_TIMEOUT
            )
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise
        encoding = locale.getpreferredencoding(False)
        return SimpleNamespace(
            returncode=process.returncode,
            stdout=stdout.decode(encoding),
            stderr=stderr.decode(encoding),
        )

    return asyncio.run(execute())


def simulate_qasm_probabilities(source_code):
    """Calculate ideal output probabilities for an OpenQASM 2 circuit.

    The submitted job may run in any driver's isolated environment. Start a
    child process with the Qiskit Aer driver's interpreter and PYTHONPATH so
    the caller does not need Qiskit installed in its own environment.
    """
    if not isinstance(source_code, str) or not source_code.strip():
        raise ValueError("source_code must be a non-empty OpenQASM string")

    python_bin, python_path_env = Library.get_driver_venv(
        QISKIT_AER_DRIVER_NAME,
        Config.DEFAULT.VENV_DIR,
        add_default_env=True,
    )
    if not python_bin or not Path(python_bin).is_absolute():
        raise ValueError(
            "Qiskit Aer driver interpreter must be an absolute path"
        )
    environment = os.environ.copy()
    environment.update(python_path_env)

    try:
        # Use a private temporary file to pass circuit source without
        # exposing it through process arguments or standard input.
        source_fd, source_name = tempfile.mkstemp(
            prefix="qcos-ideal-", suffix=".qasm"
        )
        source_path = Path(source_name)
        try:
            with os.fdopen(source_fd, "w", encoding="utf-8") as source_file:
                source_file.write(source_code)
            completed = _run_command(
                [
                    python_bin,
                    "-m",
                    "wy_qcos.driver.qiskit.driver_qiskit_aer_sim",
                    "--ideal-probabilities",
                    str(source_path),
                ],
                environment,
            )
        finally:
            source_path.unlink(missing_ok=True)
    except (OSError, TimeoutError) as error:
        raise ValueError(
            f"unable to start Qiskit Aer ideal simulator: {error}"
        ) from error

    if completed.returncode != 0:
        error_message = completed.stderr.strip() or "unknown subprocess error"
        raise ValueError(
            f"Qiskit Aer ideal simulation failed: {error_message}"
        )

    try:
        probabilities = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(
            "Qiskit Aer ideal simulator returned invalid JSON"
        ) from error
    if not isinstance(probabilities, dict):
        raise ValueError("Qiskit Aer ideal simulator returned invalid results")
    return probabilities
