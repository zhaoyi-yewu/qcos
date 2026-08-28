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

import logging
from schema import Optional

from wy_qcos.log.logger import log_perf
from wy_qcos.transpiler.common.utils import (
    TranspileRuntime,
    Timer,
)
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.mapping.aggregate.hierachy_tree import (
    HierarchyTree,
    get_block,
)
from wy_qcos.transpiler.cmss.mapping.empty_mapping import (
    EmptyRoute,
    aggregate_empty_route_results,
)
from wy_qcos.transpiler.cmss.mapping.mapping_factory import MappingFactory
from wy_qcos.transpiler.cmss.mapping.sc_mapping import (
    SCRoute,
    SC_MAPPING_OPTIONS_SCHEMA,
)
from wy_qcos.transpiler.common.errors import TranspilerException
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.transpiler.cmss.compiler.openqasm3.parser import (
    parse as openqasm3_parse,
)
from wy_qcos.transpiler.high_performance import (
    qasm_to_ir,
    sabre_routing as cpp_sabre_routing,
    transpile_from_qasm as cpp_transpile_from_qasm,
    transpile_from_ir as cpp_transpile_from_ir,
    transpile_na as cpp_transpile_na,
    cpp_na_default_routing,
)
from wy_qcos.transpiler.cmss.mapping.sc_mapping import (
    DEFAULT_SC_MAPPING_OPTIONS,
)
from wy_qcos.transpiler.cmss.mapping.utils.sabre_utils import (
    extract_topology_data,
)

logger = logging.getLogger(__name__)


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
            "target_bits": [],
        }
        # transpiler_options schema used in submit-job from user
        self.transpiler_options_schema = {
            Optional("optimization_level"): int,
            Optional("enable_na_move"): bool,
            Optional("na_mapping_type"): str,
            Optional("enable_mapping"): bool,
            Optional("sc_mapping_options"): SC_MAPPING_OPTIONS_SCHEMA,
            Optional("target_bits"): [int],
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
            init_layout_dict = {}
            final_layout_dict = {}
            mapping_res, mapping_dict = aggregate_empty_route_results(
                opt_result_dict
            )
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
            # Determine routing algorithm based on tech_type and options
            if (
                trans_cfg_inst.get_tech_type()
                == Constant.TECH_TYPE_SUPERCONDUCTING
            ):
                routing_algorithm = sc_mapping_options.get(
                    "routing_algorithm",
                    DEFAULT_SC_MAPPING_OPTIONS["routing_algorithm"],
                )
            elif (
                trans_cfg_inst.get_tech_type()
                == Constant.TECH_TYPE_NEUTRAL_ATOM
            ):
                routing_algorithm = na_mapping_type
            else:
                raise TranspilerException(
                    f"Unsupported tech_type({trans_cfg_inst.get_tech_type()}) "
                    "for mapping."
                )
            # execute mapping based on routing algorithm
            if routing_algorithm == "sabre":
                coupling_list, edge_fidelities, single_qubit_fidelities = (
                    extract_topology_data(qpu_cfg)
                )
                mapping_res = cpp_sabre_routing(
                    value[1],
                    coupling_list,
                    edge_fidelities=edge_fidelities,
                    single_qubit_fidelities=single_qubit_fidelities,
                )
            elif routing_algorithm == "default" and enable_na_move:
                mapping_res, final_layout = cpp_na_default_routing(
                    value[1], qpu_cfg, value[0]
                )
                final_layout_dict[key] = final_layout
                return (
                    mapping_res,
                    mapping_dict,
                    init_layout_dict,
                    final_layout_dict,
                )
            else:
                with Timer() as mapping_pre_timer:
                    mapper.prepare_data(value[0], value[1], qpu_cfg)
                log_perf(
                    logger,
                    f"mapping(prepare_data):{mapping_pre_timer.elapsed:.4f}s\n",
                )
                with Timer() as mapping_exec_timer:
                    mapping_res, final_layout = mapper.execute_with_order()

                final_layout_dict[key] = final_layout
                init_layout_dict[key] = mapper.initial_layout
                logger.debug(f"after mapping: {mapping_res}")
                log_perf(
                    logger,
                    "mapping(execute_with_order): "
                    f"{mapping_exec_timer.elapsed:.4f}s\n",
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
                logger.debug(f"xxblock: {blk}")
                # 使用b+树进行block查找
                # TODO (wangjujun): use b+ tree by parameter.
                # blk = get_block_bplus(ht, value[0])
                if blk is None:
                    # TODO (xudong): need to remove the task item.
                    self.total_qubits -= value[0]
                    continue
                mapping_dict[key] = value[0]
                if isinstance(mapper, SCRoute):
                    logger.debug(f"set current_block to {blk}")
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

    def transpile_single(self, qasm_string, supp_basis_gates, qpu_cfg):
        """All-in-one transpile using C++ implementation (single-circuit path).

        Selects the routing path by tech_type:
        - neutral_atom with enable_na_move -> NA mapping
          (NARoute, inserting MOVE between storage/operate areas);
        - otherwise (including superconducting) -> SABRE routing.

        Combines parse + transpile into a single C++ call, avoiding
        intermediate Python/C++ data transfer overhead.

        Args:
            qasm_string (str): QASM circuit string.
            supp_basis_gates (list[str]): Supported basis gate names.
            qpu_cfg (dict): QPU configuration dict (must contain coupler_map;
                the NA path additionally needs storage_area/operate_area/
                readout_error).

        Returns:
            TranspileResult: Contains basis_gate_list, num_qubits, and timings.
        """
        tech_type = trans_cfg_inst.get_tech_type()
        enable_na_move = self.transpiler_options.get("enable_na_move", False)
        opt_level = self.transpiler_options.get(
            "optimization_level", Constant.DEFAULT_OPTIMIZATION_LEVEL
        )

        # neutral_atom + enable_na_move -> NA mapping path
        if tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM and enable_na_move:
            # NA topology only supports cz as the two-qubit gate
            if supp_basis_gates is None or len(supp_basis_gates) == 0:
                supp_basis_gates = [
                    Constant.SINGLE_QUBIT_GATE_RX,
                    Constant.SINGLE_QUBIT_GATE_RY,
                    Constant.TWO_QUBIT_GATE_CZ,
                ]
            elif Constant.TWO_QUBIT_GATE_CZ not in supp_basis_gates:
                raise TranspilerException(
                    f"Basis gate({supp_basis_gates}) is not supported for "
                    "neutral atom topology. "
                )
            try:
                return cpp_transpile_na(
                    qasm_string,
                    supp_basis_gates,
                    qpu_cfg,
                    opt_level=opt_level,
                )
            except RuntimeError as e:
                raise TranspilerException(
                    f"C++ transpile_na failed: {e}"
                ) from e
        elif tech_type == Constant.TECH_TYPE_SUPERCONDUCTING:
            # Other (including superconducting SABRE) paths
            coupling_list, edge_fidelities, single_qubit_fidelities = (
                extract_topology_data(qpu_cfg)
            )

            try:
                return cpp_transpile_from_qasm(
                    qasm_string=qasm_string,
                    supp_basis_gates=supp_basis_gates,
                    coupling_list=coupling_list,
                    opt_level=opt_level,
                    edge_fidelities=edge_fidelities,
                    single_qubit_fidelities=single_qubit_fidelities,
                )
            except RuntimeError as e:
                raise TranspilerException(f"C++ transpile failed: {e}") from e
        else:
            raise TranspilerException(
                f"Unsupported tech_type({tech_type}) "
                "for high-performance transpiler."
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
                logger.debug(f"source_code:\n{value}")
                num_qubits = 0
                parse_result = []
                if code_type in [
                    Constant.CODE_TYPE_QASM,
                    Constant.CODE_TYPE_QASM2,
                ]:
                    try:
                        parse_result, num_qubits = qasm_to_ir(value)
                    except RuntimeError as e:
                        raise TranspilerException(
                            f"QASM parse failed: {e}"
                        ) from e
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
            if supp_basis_gates is None or len(supp_basis_gates) == 0:
                supp_basis_gates = [
                    Constant.SINGLE_QUBIT_GATE_RX,
                    Constant.SINGLE_QUBIT_GATE_RY,
                    Constant.TWO_QUBIT_GATE_CZ,
                ]
            elif Constant.TWO_QUBIT_GATE_CZ not in supp_basis_gates:
                raise TranspilerException(
                    f"Basis gate({supp_basis_gates}) is not supported for "
                    "neutral atom topology. "
                )

        enable_mapping = self.transpiler_options.get("enable_mapping", True)
        target_bits = self.transpiler_options.get("target_bits", [])
        run_time: TranspileRuntime = self.transpiler_runtime

        # get optimization level
        opt_level = self.transpiler_options.get(
            "optimization_level", Constant.DEFAULT_OPTIMIZATION_LEVEL
        )

        qpu_cfg = trans_cfg_inst.get_qpu_cfg() or {}
        if enable_mapping and not qpu_cfg:
            err_msg = "Missing qpu configs"
            logger.error(err_msg)
            raise ValueError(err_msg)

        if enable_mapping:
            coupling_list, edge_fidelities, single_qubit_fidelities = (
                extract_topology_data(qpu_cfg)
            )
        else:
            coupling_list, edge_fidelities, single_qubit_fidelities = (
                [],
                [],
                [],
            )

        timing_attrs = (
            "parse_time",
            "opt_time1",
            "decompose_1q2q_time",
            "decompose_rule_time",
            "mapping_time",
            "decompose_apply_time",
            "opt_time2",
            "transpile_time",
            "total_time",
        )

        basis_gate_list = []
        mapping_dict = {}
        final_layout_dict = {}
        for job_id, (num_qubits, ir_ops) in parse_result.items():
            try:
                result = cpp_transpile_from_ir(
                    ir_ops,
                    num_qubits,
                    supp_basis_gates,
                    opt_level,
                    coupling_list,
                    edge_fidelities=edge_fidelities,
                    single_qubit_fidelities=single_qubit_fidelities,
                    target_bits=target_bits if enable_mapping else [],
                )
            except RuntimeError as exc:
                raise TranspilerException(
                    f"C++ transpile failed: {exc}"
                ) from exc

            basis_gate_list.extend(result.basis_gate_list)
            mapping_dict[job_id] = num_qubits
            final_layout_dict[job_id] = {
                i: phys
                for i, phys in enumerate(result.final_mapping)
                if phys >= 0
            }

            cpp_timings = result.timings
            for attr in timing_attrs:
                setattr(run_time, attr, getattr(cpp_timings, attr))

        logger.debug(f"final basis_gate_list: {basis_gate_list}")
        return basis_gate_list, mapping_dict, final_layout_dict
