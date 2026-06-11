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

from schema import Optional

from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.transpiler.common.utils import (
    TranspileRuntime,
    Timer,
    trans_logger,
)
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.compiler.decomposer import (
    decompose_gates_to_1q2q,
)
from wy_qcos.transpiler.cmss.mapping.aggregate.hierachy_tree import (
    HierarchyTree,
    get_block,
)
from wy_qcos.transpiler.cmss.mapping.empty_mapping import EmptyRoute
from wy_qcos.transpiler.cmss.mapping.mapping_factory import MappingFactory
from wy_qcos.transpiler.cmss.mapping.sc_mapping import (
    SCRoute,
    SC_MAPPING_OPTIONS_SCHEMA,
)

from wy_qcos.transpiler.cmss.mapping.utils import dg_swap_opt
from wy_qcos.transpiler.common.errors import TranspilerException
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.transpiler.cmss.compiler.openqasm3.parser import (
    parse as openqasm3_parse,
)
from wy_qcos.transpiler.high_performance import (
    convert_qasm_string_to_qcos_operations,
    Decomposer,
    BaseOperation as CppBaseOperation,
    sabre_routing as cpp_sabre_routing,
    optimize,
)
from wy_qcos.transpiler.cmss.mapping.sc_mapping import (
    DEFAULT_SC_MAPPING_OPTIONS,
)
from wy_qcos.transpiler.cmss.mapping.utils.sabre_utils import (
    normalize_topology,
)
from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE


class TranspilerHighPerformanceCmss(TranspilerBase):
    """Transpiler Class for High Performance CMSS."""

    def __init__(
        self,
        optimization_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
        enable_na_move: bool = False,
        na_mapping_type: str = "default",
        enable_mapping: bool = True,
    ):
        super().__init__()
        self.total_qubits = 0
        self.name = Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS
        # alias name
        self.alias_name = "五岳高性能转译器"
        # version
        self.version = "0.1"
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3,
        ]
        # transpiler_options
        if (
            optimization_level < Constant.MIN_OPTIMIZATION_LEVEL
            or optimization_level > Constant.MAX_OPTIMIZATION_LEVEL
        ):
            raise TranspilerException(f"""
                optimization_level should be between
                {Constant.MIN_OPTIMIZATION_LEVEL} and
                {Constant.MAX_OPTIMIZATION_LEVEL}
                """)
        self.transpiler_options = {
            # default optimization level
            "optimization_level": optimization_level,
            "enable_na_move": enable_na_move,
            "na_mapping_type": na_mapping_type,
            "enable_mapping": enable_mapping,
            # sc_mapping options
            "sc_mapping_options": {},
        }
        # transpiler_options schema used in submit-job from user
        self.transpiler_options_schema = {
            Optional("optimization_level"): int,
            Optional("enable_na_move"): bool,
            Optional("na_mapping_type"): str,
            Optional("enable_mapping"): bool,
            Optional("sc_mapping_options"): SC_MAPPING_OPTIONS_SCHEMA,
        }
        # qpu_config
        self.qpu_config = None
        self.transpiler_runtime = TranspileRuntime()

    def init_transpiler(self):
        """Init transpiler."""

    @staticmethod
    def _resolve_storage_area_for_block(qpu_cfg, blk):
        """按配置自动推导 block 对应的 storage_area.

        兼容两种配置格式：
        1) 旧格式：通过 closest 从 operate_area 映射到 storage_area
        2) 新格式：operate/storage 同名坐标，直接复用 block
        """
        closest = qpu_cfg.get("closest", {})
        if closest:
            return [closest.get(o, o) for o in blk]
        return blk.copy()

    @staticmethod
    def _has_closest_mapping(qpu_cfg):
        return bool(qpu_cfg.get("closest", {}))

    def mapping(self, qpu_cfg, opt_result_dict):
        """Mapping.

        Args:
            qpu_cfg: qpu_cfg
            opt_result_dict: opt_result_dict
        Return:
            mapping_res: mapping result.
            mapping_dict; mapping dict.
            init_layout_dict: initial layout dict.
            final_layout_dict: final layout dict.
        """
        factory = MappingFactory()

        enable_na_move = self.transpiler_options.get("enable_na_move", False)
        na_mapping_type = self.transpiler_options.get(
            "na_mapping_type", "default"
        )
        sc_mapping_options = self.transpiler_options.get(
            "sc_mapping_options", {}
        )
        mapper = factory.get_mapper_by_type(
            trans_cfg_inst.get_tech_type(), enable_na_move, na_mapping_type
        )
        if isinstance(mapper, EmptyRoute):
            mapping_dict = {}
            init_layout_dict = {}
            final_layout_dict = {}
            key, value = list(opt_result_dict.items())[0]
            mapping_dict[key] = value[0]
            mapping_res = value[1]
            return (
                mapping_res,
                mapping_dict,
                init_layout_dict,
                final_layout_dict,
            )

        # set sc_mapping_options
        if isinstance(mapper, SCRoute) and sc_mapping_options:
            mapper.set_sc_mapping_options(sc_mapping_options)

        mapping_dict = {}
        final_layout_dict = {}
        init_layout_dict = {}
        if len(opt_result_dict) == 1:
            key, value = list(opt_result_dict.items())[0]
            mapping_dict[key] = value[0]
            routing_algorithm = sc_mapping_options.get(
                "routing_algorithm",
                DEFAULT_SC_MAPPING_OPTIONS["routing_algorithm"],
            )
            if routing_algorithm == "sabre":
                mapping_res = sabre_routing(value[1], qpu_cfg)
            else:
                with Timer() as mapping_pre_timer:
                    mapper.prepare_data(value[0], value[1], qpu_cfg)
                trans_logger.log_perf(
                    f"mapping(prepare_data):{mapping_pre_timer.elapsed:.4f}s\n"
                )
                with Timer() as mapping_exec_timer:
                    mapping_res, final_layout = mapper.execute_with_order()

                final_layout_dict[key] = final_layout
                init_layout_dict[key] = mapper.initial_layout
                trans_logger.log_debug(f"after mapping: {mapping_res}")
                trans_logger.log_perf(
                    "mapping(execute_with_order): "
                    f"{mapping_exec_timer.elapsed:.4f}s\n"
                )
            return (
                mapping_res,
                mapping_dict,
                init_layout_dict,
                final_layout_dict,
            )
        else:
            ht = HierarchyTree(qpu_cfg)
            ht.construct()
            mapping_res = []
            original_operate_area = qpu_cfg.get("operate_area", []).copy()
            for key, value in opt_result_dict.items():
                # 不使用b+树进行block查找
                blk = get_block(ht, value[0])
                trans_logger.log_debug(f"xxblock: {blk}")
                # 使用b+树进行block查找
                # TODO (wangjujun): use b+ tree by parameter.
                # blk = get_block_bplus(ht, value[0])
                if blk is None:
                    # TODO (xudong): need to remove the task item.
                    self.total_qubits -= value[0]
                    continue
                mapping_dict[key] = value[0]
                if isinstance(mapper, SCRoute):
                    trans_logger.log_debug(f"set current_block to {blk}")
                    # For SC, set current_block to limit the mapping range
                    qpu_cfg["current_block"] = blk
                else:
                    if self._has_closest_mapping(qpu_cfg):
                        # 旧格式：blk 为 operate block
                        qpu_cfg["operate_area"] = blk
                    else:
                        # 新格式：blk 为 storage block，
                        # operate_area 保持原始配置
                        qpu_cfg["operate_area"] = original_operate_area.copy()
                    storage_blk = self._resolve_storage_area_for_block(
                        qpu_cfg, blk
                    )
                    qpu_cfg["storage_area"] = storage_blk

                mapper.prepare_data(value[0], value[1], qpu_cfg)
                mapping_result, final_layout = mapper.execute_with_order()
                mapping_res += mapping_result
                final_layout_dict[key] = final_layout
                init_layout_dict[key] = mapper.initial_layout

            return (
                mapping_res,
                mapping_dict,
                init_layout_dict,
                final_layout_dict,
            )

    def parse(self, src_code_dict, code_type: str = Constant.CODE_TYPE_QASM):
        """Parse src_code_dict.

        Args:
          src_code_dict(dict): src_code_dict
          code_type(str): code type

        Returns:
            parse result(QuantumCircuit): quantum circuit parsed by cmss
        """
        # compile
        parse_result_dict = {}
        self.total_qubits = 0
        if isinstance(src_code_dict, dict):
            for key, value in src_code_dict.items():
                trans_logger.log_debug(f"source_code:\n{value}")
                num_qubits = 0
                parse_result = []
                if code_type in [
                    Constant.CODE_TYPE_QASM,
                    Constant.CODE_TYPE_QASM2,
                ]:
                    parse_result, num_qubits = (
                        convert_qasm_string_to_qcos_operations(value)
                    )
                else:
                    circuit = openqasm3_parse(value)
                    num_qubits = circuit.num_qubits
                    parse_result = circuit.get_operations()
                self.total_qubits += num_qubits
                parse_result_dict[key] = (num_qubits, parse_result)
            return parse_result_dict
        else:
            raise TranspilerException("unsupported input")

    def transpile(self, parse_result, supp_basis_gates: list):
        """CMSS transpiler function.

        Args:
          parse_result: parse result
          supp_basis_gates: supported basis gates

        Returns:
            basis gate list(list): basis gate list by cmss transpiler
            mapping_dict(dict): mapping dict by cmss mapping.
            only for neutral atom now
        """
        enable_na_move = self.transpiler_options.get("enable_na_move", False)
        # support cz gate for NARoute
        if enable_na_move:
            supp_basis_gates = [
                Constant.SINGLE_QUBIT_GATE_RX,
                Constant.SINGLE_QUBIT_GATE_RY,
                Constant.TWO_QUBIT_GATE_CZ,
            ]

        enable_mapping = self.transpiler_options.get("enable_mapping", True)
        run_time: TranspileRuntime = self.transpiler_runtime

        # get optimization level
        opt_level = self.transpiler_options.get(
            "optimization_level", Constant.DEFAULT_OPTIMIZATION_LEVEL
        )
        # parse dict, job_id: str, cir_info: tuple(num_qubits, circuit)
        # optimize gates list firstly for better decomposed efficiency.
        opt_result_dict = {}
        with Timer() as optimize1_timer:
            for job_id, cir_info in parse_result.items():
                opt_result = optimize(cir_info[1], opt_level=min(1, opt_level))
                opt_result_dict[job_id] = (cir_info[0], opt_result)
        run_time.opt_time1 = optimize1_timer.elapsed
        trans_logger.log_perf(
            f"tranpiler(optimize firstly): {optimize1_timer.elapsed:.4f}s\n"
        )

        if enable_mapping:
            qpu_cfg = trans_cfg_inst.get_qpu_cfg()
            if not qpu_cfg:
                err_msg = "Missing qpu configs"
                trans_logger.log_error(err_msg)
                raise ValueError(err_msg)

            # decompose gate to 1q2q gates for mapping
            dp_result_dict = {}
            with Timer() as decompose_1q2q_timer:
                for job_id, cir_info in opt_result_dict.items():
                    decomposed_gates = decompose_gates_to_1q2q(cir_info[1])
                    dp_result_dict[job_id] = (cir_info[0], decomposed_gates)
            run_time.decompose_1q2q_time = decompose_1q2q_timer.elapsed
            trans_logger.log_perf(
                "tranpiler(decomposing firstly): "
                f"{decompose_1q2q_timer.elapsed:.4f}s\n"
            )

            decomposer = Decomposer()
            decompose_rules_dict = {}
            # Flatten all BaseOperation lists from the qasm_dict values.
            gate_name_list = list({
                op.name for _, ops in dp_result_dict.values() for op in ops
            })
            with Timer() as decompose_ruler_timer:
                decompose_rules_dict, gate_depth = (
                    decomposer.get_decompose_rules(
                        gate_name_list,
                        supp_basis_gates,
                    )
                )
                dg_swap_opt.gate_depth = gate_depth.copy()
            run_time.decompose_rule_time = decompose_ruler_timer.elapsed
            trans_logger.log_perf(
                "tranpiler(get decompose rules): "
                f"{decompose_ruler_timer.elapsed:.4f}s\n"
            )

            with Timer() as mapping_timer:
                mapping_res, mapping_dict, _, _ = self.mapping(
                    qpu_cfg, dp_result_dict
                )
            run_time.mapping_time = mapping_timer.elapsed
            trans_logger.log_perf(
                f"tranpiler(mapping): {mapping_timer.elapsed:.4f}s\n"
            )

            with Timer() as applier_timer:
                decomposer_circuit = decomposer.apply_decompose_rules(
                    mapping_res, decompose_rules_dict
                )
            run_time.decompose_apply_time = applier_timer.elapsed
            trans_logger.log_perf(
                f"tranpiler(applier_timer): {applier_timer.elapsed:.4f}s\n"
            )

            # secondly optimize
            with Timer() as optimize2_timer:
                basis_gate_list = optimize(
                    decomposer_circuit,
                    opt_level,
                    basis_gates=set(supp_basis_gates),
                )
            run_time.opt_time2 = optimize2_timer.elapsed
            trans_logger.log_debug(f"final basis_gate_list: {basis_gate_list}")
            trans_logger.log_perf(
                "tranpiler(optimize secondly):"
                f" {optimize2_timer.elapsed:.4f}s\n"
            )
        else:
            decomposer = Decomposer()
            decompose_rules_dict = {}
            # Flatten all BaseOperation lists from the qasm_dict values.
            gate_name_list = list({
                op.name for _, ops in opt_result_dict.values() for op in ops
            })

            with Timer() as decompose_ruler_timer:
                decompose_rules_dict, _ = decomposer.get_decompose_rules(
                    gate_name_list,
                    supp_basis_gates,
                )
            run_time.decompose_rule_time = decompose_ruler_timer.elapsed
            trans_logger.log_perf(
                "tranpiler(get decompose rules): "
                f"{decompose_ruler_timer.elapsed:.4f}s\n"
            )

            decomposer_dict = {}
            with Timer() as applier_timer:
                for job_id, cir_info in opt_result_dict.items():
                    decomposer_dict[job_id] = decomposer.apply_decompose_rules(
                        cir_info[1], decompose_rules_dict
                    )
            run_time.decompose_apply_time = applier_timer.elapsed
            trans_logger.log_perf(
                f"tranpiler(applier_timer): {applier_timer.elapsed:.4f}s\n"
            )

            # secondly optimize
            basis_gates_dict = {}
            with Timer() as optimize2_timer:
                for job_id, ir in decomposer_dict.items():
                    basis_gates_dict[job_id] = optimize(
                        ir,
                        opt_level,
                        basis_gates=set(supp_basis_gates),
                    )
            run_time.opt_time2 = optimize2_timer.elapsed
            basis_gate_list = [
                gate for gates in basis_gates_dict.values() for gate in gates
            ]
            trans_logger.log_debug(f"final basis_gate_list: {basis_gate_list}")
            trans_logger.log_perf(
                "tranpiler(optimize secondly):"
                f" {optimize2_timer.elapsed:.4f}s\n"
            )
            mapping_dict = None

        return basis_gate_list, mapping_dict


def sabre_routing(
    ir: list,
    topology,
    initial_l2p: list[int] | None = None,
    extension_size: int = 20,
    weight: float = 0.5,
    decay: float = 0.001,
):
    """Route a single circuit with SABRE."""
    if not isinstance(ir, list):
        raise TypeError(
            "Ir must be a single-circuit list of BaseOperation instances"
        )

    coupling_list = normalize_topology(topology)

    if len(ir) == 0:
        return ir

    first_op = ir[0]
    if isinstance(first_op, BaseOperation):
        sabre = SABRE(
            coupling_list=coupling_list,
            extension_size=extension_size,
            weight=weight,
            decay=decay,
        )
        sabre.execute(ir, initial_l2p)
        return sabre.phy_exe_gates

    if CppBaseOperation is not None and isinstance(first_op, CppBaseOperation):
        initial_l2p = [] if initial_l2p is None else initial_l2p
        return cpp_sabre_routing(
            ir, coupling_list, initial_l2p, extension_size, weight, decay
        )

    raise TypeError(
        "Ir must be a single-circuit list of BaseOperation instances"
    )
