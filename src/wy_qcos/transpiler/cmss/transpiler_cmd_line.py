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
import json
import itertools


from wy_qcos.common.config import Config
from wy_qcos.log.logger import init_logger, PerfFilter, PERF_LEVEL, log_perf
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.common.utils import (
    Timer,
    TranspilePerfConstant as TPC,
    TranspileRuntime,
)
from wy_qcos.transpiler.cmss.transpiler_cmss_for_cpp import (
    TranspilerHighPerformanceCmss,
)
from wy_qcos.transpiler.cmss.mapping.sc_mapping import (
    DEFAULT_SC_MAPPING_OPTIONS,
)
from wy_qcos.transpiler.common.errors import TranspilerException
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit

logger = logging.getLogger(__name__)


class TranspileParams:
    """Transpile prameters for a single run."""

    def __init__(self):
        # base transpile configs
        self.output_log = ""
        self.csv_file = ""
        self.file = "samples/qasm/2.0/simple-qasm.qasm"
        # circuit info
        self.num_qubits = 0
        self.depth = 0
        # transpiler configs
        self.tech_gates = []
        # optimization level, 0, 1, 2, 3
        self.enable_transpiler = True
        self.opt_level = 1
        # mapping configs
        self.enable_mapping = True
        self.mapping_info = ()
        self.sc_mapping_options = {}


class CMSSTranspilerPerf:
    def __init__(self):
        # list of TranspileParams
        self.params_list = []
        # dict[TranspileParams, TranspileRuntime]
        self.transpile_result = {}
        # base transpile configs
        self.run_count = 1
        self.output_log = ""
        self.csv_file = ""
        self.file_list = ["samples/qasm/2.0/simple-qasm.qasm"]
        self.dir_list = []
        self.total_files = []
        self.perf_enabled = False
        # whether to enable the C++ all-in-one transpile (single-circuit
        # sabre routing path); defaults to True
        self.enable_transpile_single = True
        # transpiler configs
        self.base_gates = []
        # optimization level, 0, 1, 2, 3
        self.enable_transpiler = True
        self.opt_level = [1]
        # mapping configs
        self.enable_mapping = True
        self.na_mapping_type = "default"
        self.tech_type = []
        self.mapping_config_file = []
        self.mapping_info = []
        self.sc_mapping_options = []
        self.gates_map = {
            "x": Constant.SINGLE_QUBIT_GATE_X,
            "y": Constant.SINGLE_QUBIT_GATE_Y,
            "z": Constant.SINGLE_QUBIT_GATE_Z,
            "t": Constant.SINGLE_QUBIT_GATE_T,
            "tdg": Constant.SINGLE_QUBIT_GATE_TDG,
            "h": Constant.SINGLE_QUBIT_GATE_H,
            "rx": Constant.SINGLE_QUBIT_GATE_RX,
            "ry": Constant.SINGLE_QUBIT_GATE_RY,
            "rz": Constant.SINGLE_QUBIT_GATE_RZ,
            "cx": Constant.TWO_QUBIT_GATE_CX,
            "cy": Constant.TWO_QUBIT_GATE_CY,
            "cz": Constant.TWO_QUBIT_GATE_CZ,
        }

        self.parse_results = {}

    @staticmethod
    def init_output_head(
        output_file_path,
        file_path,
        opt_level,
        tech_type,
        config_file,
        sc_mapping_options,
    ):
        """Init output log head.

        Args:
            output_file_path(str): The output file path.
            file_path(str): The input file path.
            opt_level(int): The optimization level.
            tech_type(str): The technology type.
            config_file(str): The technology config file.
            sc_mapping_options(dict): The mapping options.
        """
        if output_file_path:
            with open(output_file_path, "a", encoding="utf-8") as f:
                f.write(
                    "--------------------------------------------------\n"
                    f"input file: {file_path}\n"
                    f"optimization level: {opt_level}\n"
                    f"technology type: {tech_type}\n"
                    f"technology config file: {config_file}\n"
                    f"mapping options: {sc_mapping_options}\n"
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

            # create output file
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

        # init input files
        self.file_list = extra_configs["transpile"].get("files", [])
        self.dir_list = extra_configs["transpile"].get("dirs", [])
        if self.file_list == [] and self.dir_list == []:
            raise ValueError("input files or dirs is not configured!")
        self.perf_enabled = extra_configs["transpile"].get(
            "perf_enabled", False
        )
        self.enable_transpile_single = extra_configs["transpile"].get(
            "enable_transpile_single", True
        )

        self.enable_transpiler = extra_configs["transpile"]["transpiler"].get(
            "enable_transpiler", True
        )
        self.opt_level = extra_configs["transpile"]["optimize"].get(
            "opt_level", [1]
        )
        base_gates = extra_configs["transpile"]["transpiler"].get(
            "base_gates", []
        )
        # parse base gates
        if base_gates:
            for gates in base_gates:
                tech_gates = gates.strip().split(",")
                gate_list = []
                for gate in tech_gates:
                    gate = gate.strip()
                    if gate in self.gates_map:
                        gate_list.append(self.gates_map[gate])
                    else:
                        raise ValueError(f"gate[{gate}] is not supported!")
                self.base_gates.append(tuple(gate_list))

        self.enable_mapping = extra_configs["transpile"]["mapping"].get(
            "enable_mapping", True
        )
        self.tech_type = extra_configs["transpile"]["mapping"].get(
            "tech_type", []
        )
        self.mapping_config_file = extra_configs["transpile"]["mapping"].get(
            "config_file", []
        )
        self.na_mapping_type = extra_configs["transpile"]["mapping"].get(
            "na_mapping_type", "default"
        )
        if len(self.tech_type) != len(self.mapping_config_file):
            raise ValueError(
                "tech_type and mapping config fileshould be in pair!"
            )
        if self.tech_type == []:
            raise ValueError("tech_type is not configured!")
        if self.mapping_config_file == []:
            raise ValueError("mapping config file is not configured!")

        self.mapping_info = list(zip(self.tech_type, self.mapping_config_file))

        # mapping config
        sc_mapping_options = extra_configs["transpile"]["mapping"].get(
            "sc_mapping_options", []
        )
        for option in sc_mapping_options:
            if option == "":
                self.sc_mapping_options.append({})
            else:
                self.sc_mapping_options.append(json.loads(option))
        len_option = len(self.sc_mapping_options)
        if len_option > len(self.mapping_info):
            raise ValueError(
                "mapping options should not be more than"
                " the number of pairs of tech_type and mapping"
                " config file!"
            )
        for _ in range(len(self.mapping_info) - len_option):
            self.sc_mapping_options.append({})

    def parse_file_args(self):
        """Parse input arguments from config file."""
        # parse input files
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

        # delete the duplicated files and keep the order
        self.total_files = list(dict.fromkeys(total_files))

    def main_cmss_transpiler(
        self,
        config_file: str = "",
        handlers=None,
    ):
        abs_config_path = Path(config_file).resolve()
        extra_configs = Config.get_extra_configs()
        Config.load_config_file(str(abs_config_path), extra_config=True)
        self.init_transpile_params(extra_configs)
        self.parse_file_args()

        # csv output is not supported when the C++ all-in-one transpile path
        # is enabled, because that path does not produce per-gate statistics
        # required by the csv report.
        if self.csv_file and self.enable_transpile_single:
            raise TranspilerException(
                "csv output is not supported when "
                "enable_transpile_single is true"
            )

        # CLI quiet mode: control what levels appear
        if handlers:
            if self.perf_enabled:
                for h in handlers:
                    h.setLevel(PERF_LEVEL)
                    h.addFilter(PerfFilter())
            else:
                for h in handlers:
                    h.setLevel(logging.WARNING)

        # combinations of tech_type, mapping_config_file and sc_mapping_options
        combinations = list(
            itertools.product(
                self.total_files,
                self.base_gates,
                self.opt_level,
                self.mapping_info,
                self.sc_mapping_options,
            )
        )

        for cell in combinations:
            params = TranspileParams()
            params.file = cell[0]
            params.tech_gates = cell[1]
            params.opt_level = cell[2]
            params.mapping_info = cell[3]
            params.sc_mapping_options = cell[4]
            self.params_list.append(params)
            self.transpile_result[params] = None

        # get the transpile result of all combinations and
        # calculate the average runtime
        self.get_transpile_result()

        _ = self.output_csv_file()

    def get_transpile_result(self):
        transpile_all_result = {}
        failed_params = []
        for _ in range(self.run_count):
            for params in self.params_list:
                log_perf(
                    logger,
                    "[parameters]\n"
                    f"input_file: {params.file}\n"
                    f"opt_level: {params.opt_level}\n"
                    f"base_gates: {params.tech_gates}\n"
                    f"tech_type: {params.mapping_info[0]}\n"
                    f"config_file: {params.mapping_info[1]}\n"
                    f"sc_mapping_options: {params.sc_mapping_options}\n",
                )
                try:
                    runtime = self.cmss_transpiler_perf_exec(
                        input_file=params.file,
                        opt_level=params.opt_level,
                        base_gates=params.tech_gates,
                        tech_type=params.mapping_info[0],
                        config_file=params.mapping_info[1],
                        sc_mapping_options=params.sc_mapping_options,
                    )
                except TranspilerException as e:
                    logger.error(f"Transpile failed for {params.file}: {e}")
                    if params not in failed_params:
                        failed_params.append(params)
                    continue
                if params in transpile_all_result:
                    transpile_all_result[params].add_runtime(runtime)
                else:
                    transpile_all_result[params] = runtime

        for params, runtime in transpile_all_result.items():
            self.transpile_result[params] = runtime

        if failed_params:
            logger.warning(
                f"{len(failed_params)} parameter combination(s) failed:"
            )
            for params in failed_params:
                logger.warning(
                    f"  - {params.file} (opt_level={params.opt_level}, "
                    f"tech_type={params.mapping_info[0]})"
                )

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
        # parse_results = dict[input_file, parse_result]
        # parse_result = tuple(num_qubits, operations)
        parse_results = self.parse_results
        total_content = []
        for params, runtime in transpile_result.items():
            params.num_qubits = parse_results[params.file][0]
            qc = QuantumCircuit(num_qubits=params.num_qubits)
            qc.append_operations(parse_results[params.file][1])
            params.depth = qc.depth()
            perf_content = []
            # The list order must be same as TranspilePerfConstant.CONS_DICT.
            # add qasm file
            perf_content.append(params.file.name)
            # add qubit number
            perf_content.append(params.num_qubits)
            # gate count
            perf_content.append(len(parse_results[params.file][1]))
            # circuit depth
            perf_content.append(params.depth)
            # tech_type
            perf_content.append(params.mapping_info[0])
            # optimize level
            perf_content.append(params.opt_level)
            # parse time
            perf_content.append(runtime.parse_time)
            perf_content.append(runtime.opt_time1)
            perf_content.append(runtime.decompose_rule_time)
            perf_content.append(runtime.decompose_1q2q_time)
            perf_content.append(runtime.mapping_time)
            # mapping time
            perf_content.append(runtime.decompose_apply_time)
            perf_content.append(runtime.decomposed_time)
            perf_content.append(runtime.opt_time2)
            perf_content.append(runtime.transpile_time)
            perf_content.append(runtime.total_time)
            perf_content.append(runtime.transpiled_gate_count)
            perf_content.append(runtime.transpiled_depth)
            total_content.append(perf_content)

        total_content = sorted(
            total_content, key=lambda x: (x[1], x[2], x[3], x[4])
        )

        csv_content = []
        csv_titles = [
            TPC.QASM_FILE,
            TPC.NUM_QUBITS,
            TPC.GATE_COUNT,
            TPC.DEPTH,
            TPC.TECH_TYPE,
            TPC.OPT_LEVEL,
            TPC.PARSE_TIME,
        ]
        # default start from 0 to 5
        l = TPC.CONS_DICT[TPC.QASM_FILE]
        r = TPC.CONS_DICT[TPC.PARSE_TIME]
        if not self.enable_transpiler:
            # parse
            csv_titles.append(TPC.TOTAL_TIME)
            for row in total_content:
                row_content = []
                row_content.extend(row[l:r])
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.PARSE_TIME]]:.4f}s"
                )
                # total time
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.TOTAL_TIME]]:.4f}s"
                )
                csv_content.append(row_content)
        elif not self.enable_mapping:
            # parse + transpile(no mapping)
            csv_titles.extend([
                TPC.OPT_TIME1,
                TPC.DECOMPOSE_RULE_TIME,
                TPC.DECOMPOSE_APPLY_TIME,
                TPC.DECOMPOSED_TIME,
                TPC.OPT_TIME2,
                TPC.TRANSPILE_TIME,
                TPC.TOTAL_TIME,
                TPC.TRANSPILED_GATE_COUNT,
                TPC.TRANSPILED_DEPTH,
            ])
            for row in total_content:
                row_content = []
                row_content.extend(row[l:r])
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.PARSE_TIME]]:.4f}s"
                )
                row_content.append(f"{row[TPC.CONS_DICT[TPC.OPT_TIME1]]:.4f}s")
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.DECOMPOSE_RULE_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.DECOMPOSE_APPLY_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.DECOMPOSED_TIME]]:.4f}s"
                )
                row_content.append(f"{row[TPC.CONS_DICT[TPC.OPT_TIME2]]:.4f}s")
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.TRANSPILE_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.TOTAL_TIME]]:.4f}s"
                )
                row_content.append(
                    row[TPC.CONS_DICT[TPC.TRANSPILED_GATE_COUNT]]
                )
                row_content.append(row[TPC.CONS_DICT[TPC.TRANSPILED_DEPTH]])
                csv_content.append(row_content)
        else:
            # parse + transpile
            csv_titles.extend([
                TPC.OPT_TIME1,
                TPC.DECOMPOSE_RULE_TIME,
                TPC.DECOMPOSE_1Q2Q_TIME,
                TPC.MAPPING_TIME,
                TPC.DECOMPOSE_APPLY_TIME,
                TPC.DECOMPOSED_TIME,
                TPC.OPT_TIME2,
                TPC.TRANSPILE_TIME,
                TPC.TOTAL_TIME,
                TPC.TRANSPILED_GATE_COUNT,
                TPC.TRANSPILED_DEPTH,
            ])
            for row in total_content:
                row_content = []
                row_content.extend(row[l:r])
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.PARSE_TIME]]:.4f}s"
                )
                row_content.append(f"{row[TPC.CONS_DICT[TPC.OPT_TIME1]]:.4f}s")
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.DECOMPOSE_RULE_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.DECOMPOSE_1Q2Q_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.MAPPING_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.DECOMPOSE_APPLY_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.DECOMPOSED_TIME]]:.4f}s"
                )
                row_content.append(f"{row[TPC.CONS_DICT[TPC.OPT_TIME2]]:.4f}s")
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.TRANSPILE_TIME]]:.4f}s"
                )
                row_content.append(
                    f"{row[TPC.CONS_DICT[TPC.TOTAL_TIME]]:.4f}s"
                )
                row_content.append(
                    row[TPC.CONS_DICT[TPC.TRANSPILED_GATE_COUNT]]
                )
                row_content.append(row[TPC.CONS_DICT[TPC.TRANSPILED_DEPTH]])
                csv_content.append(row_content)

        with open(csv_file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(csv_titles)
            writer.writerows(csv_content)

        return csv_file_path

    def cmss_transpiler_perf_exec(
        self,
        input_file: Path | None = None,
        opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
        base_gates: list = [],
        tech_type: str = "",
        config_file: str = "",
        sc_mapping_options: dict = {},
    ):
        """cmss-transpiler performance test for single run.

        Args:
            input_file (Path | None): input qasm file path
            opt_level (int): optimization level
            base_gates (list): base gates for technology type
            tech_type (str): technology type
            config_file (str): config file path of technology type
            sc_mapping_options (dict): mapping options

        Returns:
            TranspileRuntime: the runtime of phase of transpile
        """
        runtime = TranspileRuntime()
        output_file = self.output_log
        # input args check and init logger
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

        # load data from qasm file
        qasm_data = self.read_qasm_from_file(str(file_path))
        if qasm_data is None:
            raise ValueError(f"read qasm data from file[{file_path}] failed!")

        # parse the config file of qpu
        abs_config_path = Path(config_file).resolve()
        if not abs_config_path.exists():
            raise ValueError(f"config file[{config_file}] not existed!")
        chip_name = abs_config_path.stem

        qpu_config = {}
        extra_configs = Config.get_extra_configs()
        Config.load_config_file(config_file, extra_config=True)
        if tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM:
            qpu_config = extra_configs[chip_name]["transpiler"]["qpu_configs"]
            trans_cfg_inst.set_qpu_cfg(qpu_config)
            trans_cfg_inst.set_tech_type(tech_type)
            trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

            transpiler = TranspilerHighPerformanceCmss(
                optimization_level=opt_level,
                enable_na_move=True,
                na_mapping_type=self.na_mapping_type,
            )

            if len(base_gates) > 0:
                expected_basis_gates = []
                for gate in base_gates:
                    if gate in self.gates_map:
                        expected_basis_gates.append(self.gates_map[gate])
                    else:
                        raise ValueError(f"gate[{gate}] is not supported!")
            else:
                expected_basis_gates = [
                    Constant.SINGLE_QUBIT_GATE_RX,
                    Constant.SINGLE_QUBIT_GATE_RY,
                    Constant.TWO_QUBIT_GATE_CZ,
                ]
        elif tech_type == Constant.TECH_TYPE_SUPERCONDUCTING:
            qpu_config = extra_configs[chip_name]["transpiler"]["qpu_configs"]
            trans_cfg_inst.set_qpu_cfg(qpu_config)
            trans_cfg_inst.set_tech_type(tech_type)
            trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

            transpiler = TranspilerHighPerformanceCmss(
                optimization_level=opt_level
            )
            if len(base_gates) > 0:
                expected_basis_gates = []
                for gate in base_gates:
                    if gate in self.gates_map:
                        expected_basis_gates.append(self.gates_map[gate])
                    else:
                        raise ValueError(f"gate[{gate}] is not supported!")
            else:
                expected_basis_gates = [
                    Constant.SINGLE_QUBIT_GATE_RX,
                    Constant.SINGLE_QUBIT_GATE_RY,
                    Constant.TWO_QUBIT_GATE_CX,
                ]
        else:
            transpiler = TranspilerHighPerformanceCmss(
                optimization_level=opt_level
            )
            if len(base_gates) > 0:
                expected_basis_gates = []
                for gate in base_gates:
                    if gate in self.gates_map:
                        expected_basis_gates.append(self.gates_map[gate])
                    else:
                        raise ValueError(f"gate[{gate}] is not supported!")
            else:
                expected_basis_gates = [
                    Constant.SINGLE_QUBIT_GATE_RX,
                    Constant.SINGLE_QUBIT_GATE_RY,
                    Constant.TWO_QUBIT_GATE_CX,
                ]

        # add qasm information into output log head
        self.init_output_head(
            output_file_path,
            file_path,
            opt_level,
            tech_type,
            config_file,
            sc_mapping_options,
        )
        # performace testing
        with Timer() as total_timer:
            # generate basis gates list
            log_perf(logger, "Start performace testing of cmss compiling.")

            # Decide whether the C++ all-in-one transpile (single-circuit path)
            #  can be used.
            # - superconducting + sabre -> SABRE routing
            # - neutral_atom + enable_na_move + default -> NA mapping (NARoute)
            routing_algorithm = sc_mapping_options.get(
                "routing_algorithm",
                DEFAULT_SC_MAPPING_OPTIONS["routing_algorithm"],
            )
            is_na = (
                tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM
                and self.na_mapping_type == "default"
            )
            is_sc_sabre = (
                tech_type == Constant.TECH_TYPE_SUPERCONDUCTING
                and routing_algorithm == "sabre"
            )
            use_cpp_transpile = (
                self.enable_transpile_single
                and self.enable_mapping
                and self.enable_transpiler
                and (is_na or is_sc_sabre)
            )

            if use_cpp_transpile:
                # C++ all-in-one transpile: merge parse + transpile into
                # a single C++ call
                transpiler.transpiler_options["sc_mapping_options"] = (
                    sc_mapping_options
                )
                result = transpiler.transpile_single(
                    qasm_data, expected_basis_gates, qpu_config
                )
                # populate Python TranspileRuntime from C++ TranspileTimings
                runtime = result.timings
                for label, attr in [
                    ("parse time", "parse_time"),
                    ("first optimize time", "opt_time1"),
                    ("decompose 1q2q time", "decompose_1q2q_time"),
                    ("decompose rule time", "decompose_rule_time"),
                    ("mapping time", "mapping_time"),
                    ("decompose apply time", "decompose_apply_time"),
                    ("second optimize time", "opt_time2"),
                    ("transpile", "total_time"),
                ]:
                    log_perf(
                        logger,
                        f"cpp {label}: {getattr(runtime, attr):.4f}s\n",
                    )
            else:
                # original Python flow: run parse + transpile step by step
                with Timer() as ast_timer:
                    src_code_info = {"000": qasm_data}
                    parse_result = transpiler.parse(src_code_info)
                    self.parse_results[input_file] = list(
                        parse_result.values()
                    )[0]
                runtime.parse_time = ast_timer.elapsed
                log_perf(logger, f"parse openqasm: {ast_timer.elapsed:.4f}s")

                # optimize the transpiled gates
                if self.enable_transpiler:
                    with Timer() as tranpile_timer:
                        if len(sc_mapping_options) > 0:
                            transpiler.transpiler_options[
                                "sc_mapping_options"
                            ] = sc_mapping_options
                        transpiler.transpiler_options["enable_mapping"] = (
                            self.enable_mapping
                        )
                        transpiler.transpiler_runtime = runtime

                        basis_gate_list, _ = transpiler.transpile(
                            parse_result, expected_basis_gates
                        )
                    runtime.transpile_time = tranpile_timer.elapsed
                    log_perf(
                        logger,
                        f"cmss tranpiler: {tranpile_timer.elapsed:.4f}s\n",
                    )
        runtime.total_time = total_timer.elapsed
        log_perf(
            logger,
            "total running time of cmss-transpiler:"
            f" {total_timer.elapsed:.4f}s\n\n",
        )

        # gate count and depth of the transpiled circuit, derived from the
        # final basis gate list. Computed outside the timing blocks so it
        # does not pollute the transpile/total time statistics.
        if not use_cpp_transpile and self.enable_transpiler:
            runtime.transpiled_gate_count = len(basis_gate_list)
            # num_qubits after mapping may exceed the input circuit; use the
            # qpu max qubits when available, otherwise fall back to the
            # parsed circuit size.
            transpiled_num_qubits = trans_cfg_inst.get_max_qubits()
            if transpiled_num_qubits <= 0:
                transpiled_num_qubits = self.parse_results[input_file][0]
            transpiled_qc = QuantumCircuit(num_qubits=transpiled_num_qubits)
            transpiled_qc.append_operations(basis_gate_list)
            runtime.transpiled_depth = transpiled_qc.depth()
        return runtime


def get_parse_args():
    parser = argparse.ArgumentParser(description="cmss transpiler cli")
    parser.add_argument(
        "-c",
        "--trans-config-file",
        dest="trans_config_file",
        type=str,
        default="etc/perf/transpile_conf.toml",
        help="Input config file.",
    )
    args = parser.parse_args()
    cmss_args = {
        "trans_config_file": args.trans_config_file,
    }
    return cmss_args


def main(argv=None):
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    # init logger at DEBUG level so PERF can pass;
    # handler level/filters are set after loading config
    handlers = init_logger(logging.DEBUG, console=True, quiet=False)

    # parse arguments
    cmss_args = get_parse_args()
    perf = CMSSTranspilerPerf()
    sys.exit(
        perf.main_cmss_transpiler(
            cmss_args["trans_config_file"],
            handlers,
        )
    )
