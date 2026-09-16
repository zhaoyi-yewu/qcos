#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# ----------------------------------------------------------------------

"""Run ideal simulation in the Qiskit Aer driver's environment."""

import json
import os
import subprocess  # noqa: S404 - required for the isolated driver venv

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

IDEAL_SIMULATOR_NAME = "qiskit_aer_sim"
IDEAL_SIMULATOR_TIMEOUT = 120
QISKIT_AER_DRIVER_NAME = "DriverQiskitAerSim"


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
    environment = os.environ.copy()
    environment.update(python_path_env)

    try:
        # The executable and arguments come from trusted QCOS configuration;
        # circuit source is passed via stdin and no shell is involved.
        completed = subprocess.run(  # noqa: S603
            [
                python_bin,
                "-m",
                "wy_qcos.driver.qiskit.driver_qiskit_aer_sim",
                "--ideal-probabilities",
            ],
            input=source_code,
            capture_output=True,
            text=True,
            timeout=IDEAL_SIMULATOR_TIMEOUT,
            env=environment,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
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
