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
import csv
import logging
from pathlib import Path
from datetime import datetime
import argparse
import itertools

from wy_qcos.common.config import Config
from wy_qcos.log.logger import init_logger, PerfFilter, PERF_LEVEL, log_perf
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.common.utils import (
    Timer,
    TranspilePerfConstant as TPC,
    TranspileRuntime,
)
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.qiskit.transpiler_qiskit import TranspilerQiskit

logger = logging.getLogger(__name__)

legal_basis_gates = [
    "x",
    "y",
    "z",
    "h",
    "s",
    "sdg",
    "tdg",
    "t",
    "rx",
    "ry",
    "rz",
    "u1",
    "u2",
    "u3",
    "ch",
    "crx",
    "cry",
    "crz",
    "cx",
    "cy",
    "cz",
]


class TranspileParams:
    """Transpile parameters for a single run."""

    def __init__(self):
        self.output_log = ""
        self.csv_file = ""
        self.file = "samples/qasm/2.0/simple-qasm.qasm"
        self.num_qubits = 0
        self.depth = 0
        self.basis_gates = []
        self.opt_level = 1
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING


class QiskitTranspilerPerf:
    def __init__(self):
        self.params_list = []
        self.transpile_result = {}
        self.run_count = 1
        self.output_log = ""
        self.csv_file = ""
        self.file_list = ["samples/qasm/2.0/simple-qasm.qasm"]
        self.dir_list = []
        self.total_files = []
        self.perf_enabled = False
        self.basis_gates = []
        self.opt_level = [1]
        self.config_file = ""
        self.parse_results = {}
        self.transpile_errors = {}

    @staticmethod
    def init_output_head(
        output_file_path,
        file_path,
        opt_level,
        basis_gates,
    ):
        """Init output log head.

        Args:
            output_file_path(str): The output file path.
            file_path(str): The input file path.
            opt_level(int): The optimization level.
            basis_gates(list): The basis gates.
        """
        if output_file_path:
            with open(output_file_path, "a", encoding="utf-8") as f:
                f.write(
                    "--------------------------------------------------\n"
                    f"input file: {file_path}\n"
                    f"optimization level: {opt_level}\n"
                    f"basis gates: {basis_gates}\n"
                    "--------------------------------------------------\n"
                )

    @staticmethod
    def check_file_args(input_file, output_file):
        """Check whether the input file and output file exist.

        Args:
            input_file(Path): The input file path.
            output_file(str): The output file path.

        Returns:
            file_path(Path): The resolved input file path.
            output_file_path(Path): The resolved output file path.
        """
        if not isinstance(input_file, Path):
            file_path = Path(input_file).resolve()
        else:
            file_path = input_file
        if not file_path.exists():
            raise FileNotFoundError(
                f"Input file not existed! file: {file_path}."
            )

        output_file_path = None
        if output_file != "":
            output_file_path = Path(output_file).resolve()
            if output_file_path.exists():
                logger.warning(
                    f"output file has existed! file: {output_file_path}."
                )
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file_path = output_file_path.with_stem(
                    f"{output_file_path.stem}_{timestamp}"
                )

            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(f"testing file: {input_file}.\n")

        return file_path, output_file_path

    @staticmethod
    def read_qasm_from_file(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"read file error: {e}")
            return None

    def init_transpile_params(self, extra_configs):
        """Init transpile parameters."""
        if extra_configs is None or "transpile" not in extra_configs:
            raise ValueError("configs is invalid!")

        run_count = extra_configs["transpile"].get("run_count", 1)
        if run_count <= 0:
            self.run_count = 1
        elif run_count > 5:
            self.run_count = 5
        else:
            self.run_count = run_count

        self.output_log = extra_configs["transpile"].get("output_log", "")
        self.csv_file = extra_configs["transpile"].get("csv_file", "")

        self.file_list = extra_configs["transpile"].get("files", [])
        self.dir_list = extra_configs["transpile"].get("dirs", [])
        if self.file_list == [] and self.dir_list == []:
            raise ValueError("input files or dirs is not configured!")
        self.perf_enabled = extra_configs["transpile"].get(
            "perf_enabled", False
        )

        self.opt_level = extra_configs["transpile"]["optimize"].get(
            "opt_level", [1]
        )

        self.config_file = extra_configs["transpile"]["transpiler"].get(
            "config_file", ""
        )

        basis_gates_list = extra_configs["transpile"]["basis_gates"].get(
            "gates", []
        )
        if basis_gates_list:
            for gates in basis_gates_list:
                gate_str = gates.strip()
                gate_list = []
                for gate in gate_str.split(","):
                    gate = gate.strip()
                    if gate not in legal_basis_gates:
                        raise ValueError(f"gate[{gate}] is not supported!")
                    gate_list.append(gate)
                self.basis_gates.append(gate_list)
        else:
            self.basis_gates.append([
                Constant.SINGLE_QUBIT_GATE_RX,
                Constant.SINGLE_QUBIT_GATE_RY,
                Constant.SINGLE_QUBIT_GATE_RZ,
                Constant.SINGLE_QUBIT_GATE_X,
                Constant.SINGLE_QUBIT_GATE_H,
                Constant.TWO_QUBIT_GATE_CX,
                Constant.TWO_QUBIT_GATE_CZ,
            ])

    def parse_file_args(self):
        """Parse input arguments from config file."""
        total_files = []
        for file in self.file_list:
            file_path = Path(file).resolve()
            if not file_path.exists():
                logger.warning(f"input file[{file_path}] is not existed!")
                continue
            elif os.path.isdir(file_path):
                raise ValueError(
                    f"input file[{file_path}] is not a valid file!"
                )
            if file_path.suffix != ".qasm":
                continue
            total_files.append(file_path)

        for dir in self.dir_list:
            dir_path = Path(dir).resolve()
            if not dir_path.exists():
                logger.warning(f"input dir[{dir_path}] is not existed!")
                continue
            elif not os.path.isdir(dir_path):
                raise ValueError(
                    f"input dir[{dir_path}] is not a valid directory!"
                )
            for root, _, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(os.path.join(root, file))
                    if file_path.suffix != ".qasm":
                        continue
                    total_files.append(file_path)

        if len(total_files) == 0:
            raise ValueError("no valid input file is found!")

        self.total_files = list(dict.fromkeys(total_files))

    def main_qiskit_transpiler(
        self,
        config_file: str = "",
        handlers=None,
    ):
        abs_config_path = Path(config_file).resolve()
        extra_configs = Config.get_extra_configs()
        Config.load_config_file(str(abs_config_path), extra_config=True)
        self.init_transpile_params(extra_configs)
        self.parse_file_args()

        if handlers:
            if self.perf_enabled:
                for h in handlers:
                    h.setLevel(PERF_LEVEL)
                    h.addFilter(PerfFilter())
            else:
                for h in handlers:
                    h.setLevel(logging.WARNING)

        combinations = list(
            itertools.product(
                self.total_files,
                self.basis_gates,
                self.opt_level,
            )
        )

        for cell in combinations:
            params = TranspileParams()
            params.file = cell[0]
            params.basis_gates = cell[1]
            params.opt_level = cell[2]
            self.params_list.append(params)
            self.transpile_result[params] = None

        self.get_transpile_result()

        _ = self.output_csv_file()

    def get_transpile_result(self):
        transpile_all_result = {}
        for run_idx in range(self.run_count):
            for params in self.params_list:
                log_perf(
                    logger,
                    "[parameters]\n"
                    f"input_file: {params.file}\n"
                    f"opt_level: {params.opt_level}\n"
                    f"basis_gates: {params.basis_gates}\n",
                )
                try:
                    runtime = self.qiskit_transpiler_perf_exec(
                        input_file=params.file,
                        opt_level=params.opt_level,
                        basis_gates=params.basis_gates,
                    )
                    if params in transpile_all_result:
                        transpile_all_result[params].add_runtime(runtime)
                    else:
                        transpile_all_result[params] = runtime
                except Exception as e:
                    logger.error(
                        f"transpile failed for {params.file} "
                        f"(opt_level={params.opt_level}, "
                        f"basis_gates={params.basis_gates}): {e}"
                    )
                    self.transpile_errors[params] = str(e)
                    continue

        for params, runtime in transpile_all_result.items():
            self.transpile_result[params] = runtime

    def output_csv_file(self):
        csv_file_path = None
        if self.csv_file == "":
            return None
        else:
            csv_file = self.csv_file
            csv_file_path = Path(csv_file).resolve()
            if csv_file_path.suffix != ".csv":
                raise ValueError(
                    f"csv file[{csv_file_path}] is not a csv file!"
                )
            if csv_file_path.exists():
                logger.warning(f"csv file has existed! file: {csv_file_path}.")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_file_path = csv_file_path.with_stem(
                    f"{csv_file_path.stem}_{timestamp}"
                )
        transpile_result = self.transpile_result
        parse_results = self.parse_results
        total_content = []
        for params, runtime in transpile_result.items():
            if runtime is None:
                perf_content = []
                perf_content.append(params.file.name)
                perf_content.append("")
                perf_content.append("")
                perf_content.append("")
                perf_content.append(params.tech_type)
                perf_content.append(params.opt_level)
                perf_content.append("")
                perf_content.append("")
                perf_content.append("")
                perf_content.append(str(params.basis_gates))
                perf_content.append("")
                perf_content.append("")
                perf_content.append("FAILED")
                perf_content.append(self.transpile_errors.get(params, ""))
                total_content.append(perf_content)
                continue
            if params.file not in parse_results:
                logger.warning(
                    f"skip csv output for {params.file}: parse result"
                    " not available"
                )
                continue
            params.num_qubits = parse_results[params.file][0]
            params.depth = parse_results[params.file][1]
            perf_content = []
            perf_content.append(params.file.name)
            perf_content.append(params.num_qubits)
            perf_content.append(parse_results[params.file][2])
            perf_content.append(params.depth)
            perf_content.append(params.tech_type)
            perf_content.append(params.opt_level)
            perf_content.append(runtime.parse_time)
            perf_content.append(runtime.transpile_time)
            perf_content.append(runtime.total_time)
            perf_content.append(str(params.basis_gates))
            perf_content.append(runtime.transpiled_gate_count)
            perf_content.append(runtime.transpiled_depth)
            perf_content.append("SUCCESS")
            perf_content.append("")
            total_content.append(perf_content)

        total_content = sorted(
            total_content,
            key=lambda x: (
                x[1] if isinstance(x[1], (int, float)) else -1,
                x[2] if isinstance(x[2], (int, float)) else -1,
                x[3] if isinstance(x[3], (int, float)) else -1,
                x[4],
            ),
        )

        csv_titles = [
            TPC.QASM_FILE,
            TPC.NUM_QUBITS,
            TPC.GATE_COUNT,
            TPC.DEPTH,
            TPC.TECH_TYPE,
            TPC.OPT_LEVEL,
            TPC.PARSE_TIME,
            TPC.TRANSPILE_TIME,
            TPC.TOTAL_TIME,
            "基本门集",
            TPC.TRANSPILED_GATE_COUNT,
            TPC.TRANSPILED_DEPTH,
            "状态",
            "错误信息",
        ]

        csv_content = []
        for row in total_content:
            row_content = []
            row_content.append(row[0])
            row_content.append(row[1])
            row_content.append(row[2])
            row_content.append(row[3])
            row_content.append(row[4])
            row_content.append(row[5])
            if row[12] == "SUCCESS":
                row_content.append(f"{row[6]:.4f}s")
                row_content.append(f"{row[7]:.4f}s")
                row_content.append(f"{row[8]:.4f}s")
            else:
                row_content.append(row[6])
                row_content.append(row[7])
                row_content.append(row[8])
            row_content.append(row[9])
            row_content.append(row[10])
            row_content.append(row[11])
            row_content.append(row[12])
            row_content.append(row[13])
            csv_content.append(row_content)

        with open(csv_file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(csv_titles)
            writer.writerows(csv_content)

        return csv_file_path

    def qiskit_transpiler_perf_exec(
        self,
        input_file: Path | None = None,
        opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
        basis_gates: list = [],
    ):
        """qiskit-transpiler performance test for single run.

        Args:
            input_file (Path | None): input qasm file path
            opt_level (int): optimization level
            basis_gates (list): basis gates

        Returns:
            TranspileRuntime: the runtime of each phase
        """
        runtime = TranspileRuntime()
        output_file = self.output_log
        file_path, output_file_path = self.check_file_args(
            input_file, output_file
        )
        if not file_path:
            raise ValueError(f"input file[{input_file}] is not valid!")
        if output_file_path:
            file_handler = logging.FileHandler(
                str(output_file_path), encoding="utf-8"
            )
            logger.addHandler(file_handler)

        qasm_data = self.read_qasm_from_file(str(file_path))
        if qasm_data is None:
            raise ValueError(f"read qasm data from file[{file_path}] failed!")

        if self.config_file != "":
            abs_config_path = Path(self.config_file).resolve()
            if not abs_config_path.exists():
                raise ValueError(
                    f"config file[{self.config_file}] not existed!"
                )
            chip_name = abs_config_path.stem

            Config.load_config_file(self.config_file, extra_config=True)
            extra_configs = Config.get_extra_configs()
            qpu_config = extra_configs[chip_name]["transpiler"]["qpu_configs"]
            trans_cfg_inst.set_qpu_cfg(qpu_config)
            trans_cfg_inst.set_tech_type(Constant.TECH_TYPE_SUPERCONDUCTING)
            trans_cfg_inst.set_max_qubits(qpu_config["qubits"])
            trans_cfg_inst.set_driver_name("NoDriverQiskit")
        else:
            trans_cfg_inst.set_driver_name("DriverQiskitAerSim")

        transpiler = TranspilerQiskit(opt_level=opt_level)
        src_code_info = {"000": qasm_data}

        self.init_output_head(
            output_file_path,
            file_path,
            opt_level,
            basis_gates,
        )

        log_perf(logger, "start qiskit performance testing...")
        with Timer() as total_timer:
            with Timer() as parse_timer:
                parse_result = transpiler.parse(src_code_info)
            runtime.parse_time = parse_timer.elapsed
            log_perf(logger, f"parsing OpenQASM: {parse_timer.elapsed:.4f}s")

            if input_file not in self.parse_results:
                self.parse_results[input_file] = (
                    parse_result.num_qubits,
                    parse_result.depth(),
                    len(parse_result.data),
                )

            with Timer() as transpile_timer:
                transpiled_circuit = transpiler.transpile(
                    parse_result, basis_gates
                )
            runtime.transpile_time = transpile_timer.elapsed
            log_perf(
                logger,
                f"transpile quantum circuit: {transpile_timer.elapsed:.4f}s\n",
            )

        runtime.total_time = total_timer.elapsed
        log_perf(
            logger,
            "total running time of qiskit-transpiler:"
            f" {total_timer.elapsed:.4f}s\n\n",
        )

        if transpiled_circuit is not None:
            runtime.transpiled_gate_count = len(transpiled_circuit.data)
            runtime.transpiled_depth = transpiled_circuit.depth()
        else:
            runtime.transpiled_gate_count = 0
            runtime.transpiled_depth = 0
            logger.warning("transpiled circuit is None, skipping gate count")
        return runtime


def get_parse_args():
    parser = argparse.ArgumentParser(description="qiskit transpiler cli")
    parser.add_argument(
        "-c",
        "--trans-config-file",
        dest="trans_config_file",
        type=str,
        default="etc/perf/qiskit_transpile_conf.toml",
        help="Input config file.",
    )
    args = parser.parse_args()
    qiskit_args = {
        "trans_config_file": args.trans_config_file,
    }
    return qiskit_args


def main(argv=None):
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    handlers = init_logger(logging.DEBUG, console=True, quiet=False)

    qiskit_args = get_parse_args()
    perf = QiskitTranspilerPerf()
    sys.exit(
        perf.main_qiskit_transpiler(
            qiskit_args["trans_config_file"],
            handlers,
        )
    )
