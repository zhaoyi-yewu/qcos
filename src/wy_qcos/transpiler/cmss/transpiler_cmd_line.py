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
from pathlib import Path
from datetime import datetime
import argparse
import json
import itertools

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.common.utils import Timer
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.common.utils import (
    TranspileRuntime,
    trans_logger,
)


class TranspileParams:
    """Transpile prameters for a single run."""

    def __init__(self):
        # base transpile configs
        self.output_log = ""
        self.csv_file = ""
        self.file = "samples/qasm/2.0/simple-qasm.qasm"
        self.num_qubits = 0
        # transpiler configs
        self.tech_gates = []
        # optimization level, 0, 1, 2, 3
        self.transpiler_exec = True
        self.opt_level = 1
        # mapping configs
        self.mapping_exec = True
        self.mapping_info = ()
        self.mapping_options = {}


class CMSSTranspilerPerf:
    def __init__(self):
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
        self.log_tags = []
        # transpiler configs
        self.base_gates = []
        # optimization level, 0, 1, 2, 3
        self.transpiler_exec = True
        self.opt_level = [1]
        # mapping configs
        self.mapping_exec = True
        self.tech_type = []
        self.mapping_config_file = []
        self.mapping_info = []
        self.mapping_options = []
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

    @staticmethod
    def init_output_head(
        output_file_path,
        file_path,
        opt_level,
        tech_type,
        config_file,
        mapping_options,
    ):
        """Init output log head.

        Args:
            output_file_path(str): The output file path.
            file_path(str): The input file path.
            opt_level(int): The optimization level.
            tech_type(str): The technology type.
            config_file(str): The technology config file.
            mapping_options(dict): The mapping options.
        """
        if output_file_path:
            with open(output_file_path, "a", encoding="utf-8") as f:
                f.write(
                    "--------------------------------------------------\n"
                    f"input file: {file_path}\n"
                    f"optimization level: {opt_level}\n"
                    f"technology type: {tech_type}\n"
                    f"technology config file: {config_file}\n"
                    f"mapping options: {mapping_options}\n"
                    "--------------------------------------------------\n"
                )

    @staticmethod
    def check_file_args(input_file, output_file):
        """Check whether the input file and output file exist.

        Args:
            input_file(str): The input file path.
            output_file(str): The output file path.

        Returns:
            file_path(Path): The resolved input file path.
            output_file_path(Path): The resolved output file path.
        """
        file_path = Path(input_file).resolve()
        if not file_path.exists():
            raise FileNotFoundError(
                f"Input file not existed! file: {file_path}."
            )

        output_file_path = None
        if output_file != "":
            output_file_path = Path(output_file).resolve()
            if output_file_path.exists():
                trans_logger.log_warning(
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
            trans_logger.log_error(f"read file error: {e}")
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
        self.log_tags = extra_configs["transpile"].get("log_tags", [])
        # set the allowed log tags for performance logger
        trans_logger.set_allowed_tags(self.log_tags)

        self.transpiler_exec = extra_configs["transpile"]["transpiler"].get(
            "is_exec", True
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

        self.mapping_exec = extra_configs["transpile"]["mapping"].get(
            "is_exec", True
        )
        self.tech_type = extra_configs["transpile"]["mapping"].get(
            "tech_type", []
        )
        self.mapping_config_file = extra_configs["transpile"]["mapping"].get(
            "config_file", []
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
        mapping_options = extra_configs["transpile"]["mapping"].get(
            "mapping_options", []
        )
        for option in mapping_options:
            if option == "":
                self.mapping_options.append({})
            else:
                self.mapping_options.append(json.loads(option))
        len_option = len(self.mapping_options)
        if len_option > len(self.mapping_info):
            raise ValueError(
                "mapping options should not be more than"
                " the number of pairs of tech_type and mapping"
                " config file!"
            )
        for _ in range(len(self.mapping_info) - len_option):
            self.mapping_options.append({})

    def parse_file_args(self):
        """Parse input arguments from config file."""
        # parse input files
        total_files = []
        for file in self.file_list:
            file_path = Path(file).resolve()
            if not file_path.exists():
                trans_logger.log_warning(
                    f"input file[{file_path}] is not existed!"
                )
                continue
            elif os.path.isdir(file_path):
                raise ValueError(
                    f"input file[{file_path}] is not a valid file!"
                )
            total_files.append(file_path)

        for dir in self.dir_list:
            dir_path = Path(dir).resolve()
            if not dir_path.exists():
                trans_logger.log_warning(
                    f"input dir[{dir_path}] is not existed!"
                )
                continue
            elif not os.path.isdir(dir_path):
                raise ValueError(
                    f"input dir[{dir_path}] is not a valid directory!"
                )
            for root, _, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(os.path.join(root, file))
                    total_files.append(file_path)

        if len(total_files) == 0:
            raise ValueError("no valid input file is found!")

        # delete the duplicated files and keep the order
        self.total_files = list(dict.fromkeys(total_files))

    def main_cmss_transpiler(
        self,
        config_file: str = "",
    ):
        abs_config_path = Path(config_file).resolve()
        extra_configs = Config.get_extra_configs()
        Config.load_config_file(abs_config_path, extra_config=True)
        self.init_transpile_params(extra_configs)
        self.parse_file_args()

        # combinations of tech_type, mapping_config_file and mapping_options
        combinations = list(
            itertools.product(
                self.total_files,
                self.base_gates,
                self.opt_level,
                self.mapping_info,
                self.mapping_options,
            )
        )

        for cell in combinations:
            params = TranspileParams()
            params.file = cell[0]
            params.tech_gates = cell[1]
            params.opt_level = cell[2]
            params.mapping_info = cell[3]
            params.mapping_options = cell[4]
            self.params_list.append(params)
            self.transpile_result[params] = None

        # get the transpile result of all combinations and
        # calculate the average runtime
        self.get_transpile_result()

        # TODO: output csv file

    def get_transpile_result(self):
        transpile_all_result = {}
        for _ in range(self.run_count):
            for params in self.params_list:
                runtime = self.cmss_transpiler_perf_exec(
                    input_file=params.file,
                    opt_level=params.opt_level,
                    base_gates=params.tech_gates,
                    tech_type=params.mapping_info[0],
                    config_file=params.mapping_info[1],
                    mapping_options=params.mapping_options,
                )
                if params in transpile_all_result:
                    transpile_all_result[params].add_runtime(runtime)
                else:
                    transpile_all_result[params] = runtime

        for params, runtime in transpile_all_result.items():
            runtime.avg_runtime(self.run_count)
            self.transpile_result[params] = runtime

    def cmss_transpiler_perf_exec(
        self,
        input_file: str = "",
        opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
        base_gates: list = [],
        tech_type: str = "",
        config_file: str = "",
        mapping_options: dict = {},
    ):
        """cmss-transpiler performance test for single run.

        Args:
            input_file (str): input qasm file path
            opt_level (int): optimization level
            base_gates (list): base gates for technology type
            tech_type (str): technology type
            config_file (str): config file path of technology type
            mapping_options (dict): mapping options

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
            trans_logger.set_log_file(output_file_path)

        # load data from qasm file
        qasm_data = self.read_qasm_from_file(str(file_path))
        if qasm_data is None:
            raise ValueError(f"read qasm data from file[{file_path}] failed!")

        # performace testing
        with Timer() as total_timer:
            # parse the config file of qpu
            abs_config_path = Path(config_file).resolve()
            if not abs_config_path.exists():
                raise ValueError(f"config file[{config_file}] not existed!")

            qpu_config = {}
            extra_configs = Config.get_extra_configs()
            Config.load_config_file(config_file, extra_config=True)
            if tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM:
                qpu_config = extra_configs["hanyuan1"]["transpiler"][
                    "qpu_configs"
                ]
                trans_cfg_inst.set_qpu_cfg(qpu_config)
                trans_cfg_inst.set_tech_type(tech_type)
                trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

                transpiler = TranspilerCmss(
                    optimization_level=opt_level, enable_na_move=True
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
                qpu_config = extra_configs["spinq_rpc"]["transpiler"][
                    "qpu_configs"
                ]
                trans_cfg_inst.set_qpu_cfg(qpu_config)
                trans_cfg_inst.set_tech_type(tech_type)
                trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

                transpiler = TranspilerCmss(optimization_level=opt_level)
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
                transpiler = TranspilerCmss(optimization_level=opt_level)
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
                mapping_options,
            )

            # generate basis gates list
            trans_logger.log_perf("start qiskit performace testing...")
            with Timer() as ast_timer:
                src_code_info = {"000": qasm_data}
                parse_result = transpiler.parse(src_code_info)
            runtime.parse_time = ast_timer.elapsed
            trans_logger.log_perf(f"parse openqasm: {ast_timer.elapsed:.4f}s")

            # optimize the transpiled gates
            if self.transpiler_exec:
                with Timer() as tranpile_timer:
                    if len(mapping_options) > 0:
                        transpiler.transpiler_options["sc_mapping_options"] = (
                            mapping_options
                        )
                    transpiler.transpiler_options["perf_options"] = {
                        "mapping_exec": self.mapping_exec,
                        "transpiler_time": runtime,
                    }
                    _, _ = transpiler.transpile(
                        parse_result, expected_basis_gates
                    )
                runtime.transpile_time = tranpile_timer.elapsed
                trans_logger.log_perf(
                    f"cmss tranpiler: {tranpile_timer.elapsed:.4f}s\n"
                )
        runtime.total_time = total_timer.elapsed
        trans_logger.log_perf(
            "total running time of cmss-transpiler:"
            f" {total_timer.elapsed:.4f}s"
        )
        return runtime


def get_parse_args():
    parser = argparse.ArgumentParser(description="cmss transpiler cli")
    parser.add_argument(
        "-c",
        "--trans-config-file",
        dest="trans_config_file",
        type=str,
        default="",
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

    # parse arguments
    cmss_args = get_parse_args()
    perf = CMSSTranspilerPerf()
    sys.exit(
        perf.main_cmss_transpiler(
            cmss_args["trans_config_file"],
        )
    )
