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
"""Quafu fidelity calibration.

Implements the Quafu-specific subclass of FidelityCalibrator.
Parses calibration CSV, submits CX/measurement circuits to the Quafu
cloud, collects results, and writes a TOML file matching
etc/topology/``*.toml`` format.
"""

from __future__ import annotations

import csv
import os
import time

from quark import Task

from wy_qcos.transpiler.cmss.mapping.utils.calibration_base import (
    FidelityCalibrator,
)

# Edges to skip (disconnected on server but fid>0 in CSV).
# Use normalized form (min, max). Add when server reports
# "qubits X and Y are disconnected".
SKIP_EDGES: set[tuple[int, int]] = set()


class QuafuFidelityCalibrator(FidelityCalibrator):
    """Fidelity calibrator for the Quafu cloud platform."""

    driver = "DriverQuafu"

    def __init__(
        self,
        csv_path: str,
        chip: str,
        shots: int = 1024,
        timeout: int = 300,
        submit_interval: float = 0.25,
        output_dir: str = ".",
    ):
        """Initialize the Quafu calibrator.

        Args:
            csv_path: Path to the calibration CSV file.
            chip: Quafu chip name (e.g. "Dongling").
            shots: Measurement shots per circuit.
            timeout: Timeout in seconds for a single task.
            submit_interval: Interval (seconds) between submissions.
            output_dir: Output directory for TOML file.
        """
        token = os.environ.get("QUARK_TOKEN", "")
        if not token:
            raise SystemExit("Please set QUARK_TOKEN environment variable")
        self._task_manager = Task(token)
        self.csv_path = csv_path
        self.chip = chip
        self.shots = shots
        self.timeout = timeout
        self.submit_interval = submit_interval
        self.output_dir = output_dir
        self._calibration_cache = None

    def submit(self, name: str, qasm: str) -> int:
        """Submit a circuit to the Quafu cloud (non-blocking).

        Args:
            name: Task name.
            qasm: OPENQASM 2.0 circuit text.

        Returns:
            Quafu task id (tid).
        """
        return self._task_manager.run({
            "chip": self.chip,
            "name": name,
            "circuit": qasm,
            "shots": self.shots,
            "options": {
                "compiler": None,
                "correct": False,
                "open_dd": None,
            },
        })

    def wait_result(self, task_id: int) -> dict:
        """Poll the Quafu server until the task completes.

        Args:
            task_id: Quafu task id returned by submit().

        Returns:
            Result dict containing 'count' (measurement counts).

        Raises:
            RuntimeError: Task failed.
            TimeoutError: Task did not complete within timeout.
        """
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            status = self._task_manager.status(task_id)
            if status == "Finished":
                return self._task_manager.result(task_id)
            if status == "Failed":
                result = self._task_manager.result(task_id)
                raise RuntimeError(
                    f"task {task_id} failed: {result.get('error', 'unknown')}"
                )
            time.sleep(2.0)
        raise TimeoutError(f"task {task_id} timeout ({self.timeout}s)")

    def load_calibration(
        self,
    ) -> tuple[
        list[tuple[int, int]],
        list[tuple[int, float]],
        int,
    ]:
        """Parse Quafu calibration CSV.

        Returns:
            (edges, qubit_list, qreg_size) tuple.
            Raises ValueError if no edges found.
        """
        edges: list[tuple[int, int]] = []
        qubit_list: list[tuple[int, float]] = []
        max_qubit = -1

        with open(self.csv_path, encoding="utf-8", newline="") as file:
            reader = csv.reader(file)
            next(reader, None)
            for row in reader:
                if len(row) < 6:
                    continue
                try:
                    qubit_id = int(row[0])
                    old_fid = float(row[4])
                except ValueError:
                    continue
                qubit_list.append((qubit_id, old_fid))

                cz_field = row[5]
                for line in cz_field.replace("\r", "").split("\n"):
                    line = line.strip()
                    if ":" not in line or "_" not in line:
                        continue
                    edge_key, fid_str = line.rsplit(":", 1)
                    parts = edge_key.strip().split("_")
                    if len(parts) != 2:
                        continue
                    try:
                        u, v = int(parts[0]), int(parts[1])
                        fid = float(fid_str)
                    except ValueError:
                        continue
                    max_qubit = max(max_qubit, u, v)
                    if fid > 0:
                        norm = (min(u, v), max(u, v))
                        if norm in SKIP_EDGES:
                            print(f"  SKIP ({u},{v}) fid={fid}")
                            continue
                        edges.append((u, v))

        if max_qubit < 0:
            raise ValueError(f"No edges found in {self.csv_path}")
        qreg_size = max_qubit + 1
        return edges, qubit_list, qreg_size


def calibrate(
    csv_path: str,
    chip: str = "Dongling",
    shots: int = 1024,
    timeout: int = 300,
    submit_interval: float = 0.25,
    output_dir: str = ".",
) -> str:
    """Run fidelity calibration on a Quafu chip.

    Args:
        csv_path: Path to the calibration CSV file.
        chip: Quafu chip name.
        shots: Measurement shots per circuit.
        timeout: Timeout in seconds for a single task.
        submit_interval: Interval (seconds) between submissions.
        output_dir: Output directory for TOML file.

    Returns:
        Path to the generated TOML file.
    """
    calibrator = QuafuFidelityCalibrator(
        csv_path=csv_path,
        chip=chip,
        shots=shots,
        timeout=timeout,
        submit_interval=submit_interval,
        output_dir=output_dir,
    )
    return calibrator.run()


if __name__ == "__main__":
    calibrate(
        csv_path=("xxx.csv"),
        chip="Shenglian",
    )
