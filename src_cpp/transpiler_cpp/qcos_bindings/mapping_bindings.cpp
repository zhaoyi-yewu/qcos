/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/shared_ptr.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/unordered_map.h>
#include <nanobind/stl/vector.h>

#include <stdexcept>

#include "circuit/gate_operation.h"
#include "mapping/chip_data.h"
#include "mapping/dense_layout.h"
#include "mapping/greedy_routing.h"
#include "mapping/na_mapping.h"
#include "mapping/sabre_mapping.h"
#include "mapping/sabre_routing.h"
#include "mapping/vf2_layout.h"

namespace nb = nanobind;
using namespace qcos;

namespace {

/**
 * @brief 绑定 high_performance.sabre_routing 的 C++ BaseOperation 入口。
 *
 * @param gates_list_raw Python 侧传入的 BaseOperation 对象列表。
 * @param coupling_list 物理耦合图边列表。
 * @param edge_fidelities 边保真度数组。
 * @param single_qubit_fidelities 单比特保真度数组。
 * @param layout_method 初始映射方法: "vf2_layout"(默认) 或 "dense_layout"。
 * @param target_bits 目标物理位(空=不限制); 全单比特门映射到这些位,
 * 含双比特门在其诱导子图上路由。
 * @param fidelity_threshold 保真度过滤阈值, <0 自适应计算。
 * @param fidelity_weight DenseLayout 保真度权重，取值 [0, 1]。
 * @param extension_size 扩展集大小。
 * @param weight 前沿层与扩展层成本权重。
 * @param decay SWAP 衰减系数。
 * @return nb::list 路由后的 BaseOperation 对象列表。
 */
nb::list bind_cpp_sabre_routing(
    const std::vector<qcos::BaseOperation*>& gates_list_raw,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities,
    const std::vector<double>& single_qubit_fidelities,
    const std::string& layout_method, const std::vector<int>& target_bits,
    double fidelity_threshold, double fidelity_weight, int extension_size,
    double weight, double decay) {
  std::vector<std::shared_ptr<qcos::BaseOperation>> gates_list;
  gates_list.reserve(gates_list_raw.size());
  for (auto* op : gates_list_raw) {
    if (op == nullptr) {
      throw std::invalid_argument(
          "sabre_routing received a null BaseOperation");
    }
    gates_list.push_back(op->clone());
  }

  auto routed_ops = qcos::sabre_routing(
      gates_list, coupling_list, edge_fidelities, single_qubit_fidelities,
      layout_method, target_bits, fidelity_threshold, fidelity_weight,
      extension_size, weight, decay);

  nb::list nb_list;
  for (auto& op : routed_ops) {
    nb_list.append(std::move(op));
  }
  return nb_list;
}

/**
 * @brief Parse NAQpuConfig from a Python dict.
 */
qcos::NAQpuConfig parse_na_qpu_config(const nb::dict& qpu_cfg) {
  qcos::NAQpuConfig cfg;
  nb::list storage_area = nb::cast<nb::list>(qpu_cfg["storage_area"]);
  for (auto pos : storage_area) {
    cfg.storage_area.push_back(nb::cast<std::string>(pos));
  }
  nb::list operate_area = nb::cast<nb::list>(qpu_cfg["operate_area"]);
  for (auto pos : operate_area) {
    cfg.operate_area.push_back(nb::cast<std::string>(pos));
  }
  nb::dict coupler_map = nb::cast<nb::dict>(qpu_cfg["coupler_map"]);
  for (auto item : coupler_map) {
    auto endpoints = nb::cast<std::vector<std::string>>(item.second);
    if (endpoints.size() != 2) {
      throw std::invalid_argument("coupler_map entry must have 2 endpoints");
    }
    cfg.coupler_map.emplace_back(std::string(""),
                                 std::make_pair(endpoints[0], endpoints[1]));
  }
  nb::dict readout_error = nb::cast<nb::dict>(qpu_cfg["readout_error"]);
  for (auto item : readout_error) {
    auto pos = nb::cast<std::string>(item.first);
    auto err = nb::cast<double>(item.second);
    cfg.readout_error[pos] = err;
  }
  return cfg;
}

/**
 * @brief Python entry point for NA mapping.
 *
 * @param gates_list_raw Python-side BaseOperation list.
 * @param qpu_cfg QPU config dict
 * (storage_area/operate_area/coupler_map/readout_error).
 * @param qbit_num Number of logical qubits.
 * @param na_support_move Whether the device supports MOVE + two-qubit gates;
 *        false selects NASingleRoute, true selects NADefaultRoute.
 * @param na_mapping_type NA mapping algorithm type; only "default" is supported
 *        by the C++ backend.
 * @param optimize Whether to enable overlap optimization (execute_with_opt).
 * @return nb::tuple (mapped_ops, final_layout)
 */
nb::tuple bind_na_routing(
    const std::vector<qcos::BaseOperation*>& gates_list_raw,
    const nb::dict& qpu_cfg, int qbit_num, bool na_support_move,
    const std::string& na_mapping_type, bool optimize) {
  std::vector<std::shared_ptr<qcos::BaseOperation>> gates_list;
  gates_list.reserve(gates_list_raw.size());
  for (auto* op : gates_list_raw) {
    if (op == nullptr) {
      throw std::invalid_argument("na_routing received a null BaseOperation");
    }
    gates_list.push_back(op->clone());
  }

  auto cfg = parse_na_qpu_config(qpu_cfg);

  auto res = qcos::na_mapping(gates_list, cfg, qbit_num, na_support_move,
                              na_mapping_type, optimize);

  nb::module_ gate_module =
      nb::module_::import_("wy_qcos.common.cmss.gate_operation");
  nb::object create_gate = gate_module.attr("create_gate");

  nb::list mapped_ir;
  for (auto& op : res) {
    mapped_ir.append(create_gate(op->name, op->targets, op->arg_value));
  }
  return nb::make_tuple(mapped_ir, nb::dict());
}

/**
 * @brief Python entry point for NA default routing.
 *
 * Thin wrapper around na_mapping() fixed to the "default" strategy
 * (NADefaultRoute), exposing only the inputs a single-circuit neutral-atom
 * mapping needs. Equivalent to na_routing(..., na_support_move=True,
 * na_mapping_type="default", optimize=...).
 *
 * @param gates_list_raw Python-side BaseOperation list.
 * @param qpu_cfg QPU config dict
 * (storage_area/operate_area/coupler_map/readout_error).
 * @param qbit_num Number of logical qubits.
 * @param optimize Whether to enable overlap optimization (execute_with_opt).
 * @return nb::tuple (mapped_ops, final_layout); final_layout is always empty.
 */
nb::tuple bind_cpp_na_default_routing(
    const std::vector<qcos::BaseOperation*>& gates_list_raw,
    const nb::dict& qpu_cfg, int qbit_num, bool optimize) {
  return bind_na_routing(gates_list_raw, qpu_cfg, qbit_num,
                         /*na_support_move=*/true,
                         /*na_mapping_type=*/"default", optimize);
}

}  // namespace

void bind_mapping(nb::module_& m) {
  nb::class_<ChipCalibration>(
      m, "ChipCalibration",
      "Chip calibration data: coupling graph + edge fidelities + single-qubit "
      "fidelities")
      .def(nb::init<std::vector<std::pair<int, int>>, std::vector<double>,
                    std::vector<double>>(),
           nb::arg("coupling_list"), nb::arg("edge_fidelities"),
           nb::arg("single_qubit_fidelities"))
      .def_rw("coupling_list", &ChipCalibration::coupling_list)
      .def_rw("edge_fidelities", &ChipCalibration::edge_fidelities)
      .def_rw("single_qubit_fidelities",
              &ChipCalibration::single_qubit_fidelities);

  m.def("load_chip_calibration", &qcos::load_chip_calibration,
        nb::arg("csv_path"),
        R"(
Load chip calibration data from a CSV file (北量院 format).

Args:
    csv_path (str): Path to the calibration CSV file.

Returns:
    ChipCalibration: Parsed calibration data.
        )");

  nb::class_<SABRE>(m, "SABRE", "SABRE quantum routing algorithm")
      .def(nb::init<const std::vector<std::pair<int, int>>&,
                    const std::vector<double>&, const std::vector<double>&,
                    const std::string&, const std::vector<int>&, double,
                    double, int, double, double>(),
           nb::arg("coupling_list"),
           nb::arg("edge_fidelities") = std::vector<double>{},
           nb::arg("single_qubit_fidelities") = std::vector<double>{},
           nb::arg("layout_method") = "vf2_layout",
           nb::arg("target_bits") = std::vector<int>{},
           nb::arg("fidelity_threshold") = -1.0,
           nb::arg("fidelity_weight") = 0.5, nb::arg("extension_size") = 20,
           nb::arg("weight") = 0.5, nb::arg("decay") = 0.001,
           R"(
            Construct a SABRE router.

            Args:
                coupling_list (list[tuple[int, int]]): Physical qubit connectivity
                    graph.
                edge_fidelities (list[float], optional): Edge fidelity values
                    corresponding to coupling_list. Empty means not used.
                single_qubit_fidelities (list[float], optional): Single-qubit
                    fidelity array indexed by physical qubit ID. Empty means not used.
                layout_method (str, optional): Initial layout method: "vf2_layout"
                    (default) or "dense_layout".
                target_bits (list[int], optional): Target physical qubit IDs. When
                    non-empty, all-1q circuits map to these qubits and 2q circuits
                    route on the induced subgraph of edges between them.
                fidelity_threshold (float, optional): Fidelity threshold for
                    filtering low-fidelity edges. Negative value means adaptive
                    calculation (mean - std, clamped to [0.3, 0.9]).
                    Defaults to -1.0 (adaptive).
                fidelity_weight (float, optional): DenseLayout fidelity weight in [0, 1].
                    0.0 = pure density, 1.0 = pure fidelity. Defaults to 0.5.
                extension_size (int, optional): Size of the lookahead set.
                    Defaults to 20.
                weight (float, optional): Weight between front layer and lookahead
                    cost. Defaults to 0.5.
                decay (float, optional): SWAP decay coefficient. Defaults to 0.001.
            )")

      .def("execute",
           static_cast<void (SABRE::*)(
               const std::vector<std::shared_ptr<BaseOperation>>&)>(
               &SABRE::execute),
           nb::arg("gates_list"),
           R"(
            Execute SABRE routing.

            Args:
                gates_list (list[BaseOperation]): Logical operation sequence
                    (may contain measure gates).

            Returns:
                None
            )")

      .def("get_final_mapping", &SABRE::get_final_mapping,
           R"(
            Get the final logical-to-physical mapping after routing.

            Returns:
                list[int]: The index is logical qubit and value is physical qubit.
            )")

      .def("get_initial_mapping", &SABRE::get_initial_mapping,
           R"(
            Get the initial logical-to-physical mapping.

            Must be called after execute().

            Returns:
                list[int]: The index is logical qubit and value is physical qubit.
            )")

      .def("get_physical_gates", &SABRE::get_physical_gates,
           R"(
            Get the sequence of mapped physical gates after routing (including measures).

            Returns:
                list[BaseOperation]: The physical gate sequence.
            )");

  nb::class_<GreedyRouting>(
      m, "GreedyRouting",
      "Greedy blocked-gate routing: insert a SWAP only when a gate is blocked")
      .def(nb::init<const std::vector<std::pair<int, int>>&>(),
           nb::arg("coupling_list"))
      .def("execute",
           static_cast<void (GreedyRouting::*)(
               const std::vector<GateOperation>&, const std::vector<int>&)>(
               &GreedyRouting::execute),
           nb::arg("gates_list"), nb::arg("initial_l2p") = std::vector<int>{})
      .def("get_physical_gates", &GreedyRouting::get_physical_gates)
      .def_ro("logic2phy", &GreedyRouting::logic2phy)
      .def_ro("phy2logic", &GreedyRouting::phy2logic);

  m.def("sabre_initial_mapping", &qcos::sabre_initial_mapping,
        nb::arg("gates_list"), nb::arg("coupling_list"),
        nb::arg("initial_layout") = std::vector<int>{},
        R"(
        Get the initial mapping using the SABRE algorithm.

        Args:
            gates_list (list[GateOperation]): Logical gate sequence.
            coupling_list (list[tuple[int, int]]): Physical qubit coupling list.
            initial_layout (list[int], optional): Starting layout for SABRE.
                Defaults to empty.

        Returns:
            list[int]: The initial logical-to-physical mapping.
        )");

  m.def("sabre_routing", &bind_cpp_sabre_routing, nb::arg("gates_list"),
        nb::arg("coupling_list"),
        nb::arg("edge_fidelities") = std::vector<double>{},
        nb::arg("single_qubit_fidelities") = std::vector<double>{},
        nb::arg("layout_method") = "vf2_layout",
        nb::arg("target_bits") = std::vector<int>{},
        nb::arg("fidelity_threshold") = -1.0, nb::arg("fidelity_weight") = 0.5,
        nb::arg("extension_size") = 20, nb::arg("weight") = 0.5,
        nb::arg("decay") = 0.001,
        R"(
        Execute SABRE routing.

        Args:
            gates_list (list[BaseOperation]): Logical operation sequence.
            coupling_list (list[tuple[int, int]]): Physical qubit coupling list.
            edge_fidelities (list[float], optional): Edge fidelity array
                (corresponds to coupling_list). Empty means no fidelity.
            single_qubit_fidelities (list[float], optional): Single-qubit
                fidelity array. Empty means not used.
            layout_method (str, optional): Initial layout method: "vf2_layout"
                (default) or "dense_layout".
            target_bits (list[int], optional): Target physical qubit IDs. When
                non-empty, all-1q circuits map to these qubits and 2q circuits
                route on the induced subgraph of edges between them.
            fidelity_threshold (float, optional): Fidelity threshold for
                filtering low-fidelity edges. Negative value means adaptive
                calculation (mean - std, clamped to [0.3, 0.9]).
                Defaults to -1.0 (adaptive).
            fidelity_weight (float, optional): DenseLayout fidelity weight in [0, 1].
                Defaults to 0.5.
            extension_size (int, optional): Size of the lookahead set.
                Defaults to 20.
            weight (float, optional): Weight between front layer and lookahead cost.
                Defaults to 0.5.
            decay (float, optional): SWAP decay coefficient. Defaults to 0.001.

        Returns:
            list[BaseOperation]: The routed physical operation sequence.
        )");

  m.def("dense_layout_mapping", &qcos::dense_layout_mapping,
        nb::arg("gates_list"), nb::arg("coupling_list"),
        nb::arg("edge_fidelities"), nb::arg("num_logical"),
        nb::arg("fidelity_weight") = 0.5,
        R"(
        Compute initial layout using DenseLayout + SABRE refinement.

        Two-step process:
        1. DenseLayout: find the densest connected subgraph in the coupling map
        2. SABRE refinement: use forward-backward routing to optimize qubit arrangement

        Args:
            gates_list (list[GateOperation]): Logical gate sequence.
            coupling_list (list[tuple[int, int]]): Physical coupling list (directed).
            edge_fidelities (list[float]): Edge fidelities corresponding to coupling_list.
                Pass empty list to disable fidelity-aware scoring.
            num_logical (int): Number of logical qubits declared in the circuit.
            fidelity_weight (float, optional): Fidelity weight in [0, 1] for subgraph scoring.
                0.0 = pure density, 1.0 = pure fidelity. Defaults to 0.5.

        Returns:
            list[int]: The initial logical-to-physical mapping.
        )");

  m.def("vf2_layout_mapping", &qcos::vf2_layout_mapping, nb::arg("gates_list"),
        nb::arg("coupling_list"), nb::arg("edge_fidelities"),
        nb::arg("num_logical"),
        R"(
        Compute initial layout using VF2 subgraph isomorphism.

        Attempts to find a "perfect" embedding where all two-qubit gates can
        execute directly on the coupling graph without any SWAP. If multiple
        valid embeddings exist, the one with the lowest error rate is chosen.
        Returns an empty list if no perfect embedding is found.

        Args:
            gates_list (list[GateOperation]): Logical gate sequence.
            coupling_list (list[tuple[int, int]]): Physical coupling list (directed).
            edge_fidelities (list[float]): Edge fidelities corresponding to
                coupling_list. Pass empty list to disable fidelity-aware scoring.
            num_logical (int): Number of logical qubits declared in the circuit.

        Returns:
            list[int]: The initial logical-to-physical mapping, or empty if
            no perfect embedding exists.
        )");

  m.def("na_routing", &bind_na_routing, nb::arg("gates_list"),
        nb::arg("qpu_cfg"), nb::arg("qbit_num"),
        nb::arg("na_support_move") = false,
        nb::arg("na_mapping_type") = "default", nb::arg("optimize") = false,
        R"(
        Execute neutral atom routing.

        Dispatches to a concrete NARoute strategy based on na_support_move and
        na_mapping_type, mirroring the Python-side MappingFactory dispatch:

        * na_support_move=False -> NASingleRoute: single-qubit-only layout that
          maps logical qubits to the storage area by ascending readout error.
        * na_support_move=True, na_mapping_type="default" -> NADefaultRoute:
          full two-qubit routing that inserts MOVE operations to shuttle atoms
          between the storage and operate areas so two-qubit gates act on
          adjacent sites.

        Args:
            gates_list (list[BaseOperation]): Logical operation sequence.
                Each operation's targets are logical qubit indices.
            qpu_cfg (dict): QPU configuration with keys ``storage_area``,
                ``operate_area``, ``coupler_map`` and ``readout_error``.
            qbit_num (int): Number of logical qubits.
            na_support_move (bool, optional): Whether the device supports MOVE
                + two-qubit gates. False selects NASingleRoute; True selects
                NADefaultRoute (requires na_mapping_type="default"). Defaults to
                False.
            na_mapping_type (str, optional): NA mapping algorithm type; only
                "default" is supported by the C++ backend. Defaults to
                "default".
            optimize (bool, optional): Whether to enable the overlap
                optimization (``execute_with_opt``). Strategies without one fall
                back to ``execute_with_order``. Defaults to False.

        Returns:
            tuple[list[BaseOperation], dict]: The mapped operation sequence
            (with MOVE operations and physical qubit targets when
            na_support_move is True) and an empty final layout dict.
        )");

  m.def("cpp_na_default_routing", &bind_cpp_na_default_routing,
        nb::arg("gates_list"), nb::arg("qpu_cfg"), nb::arg("qbit_num"),
        nb::arg("optimize") = false,
        R"(
        Execute neutral-atom default routing (NADefaultRoute).

        Thin wrapper around ``na_routing`` fixed to the "default" NA mapping
        strategy with MOVE support enabled, exposing only the inputs a
        single-circuit neutral-atom mapping needs. Inserts MOVE operations to
        shuttle atoms between the storage and operate areas so that two-qubit
        gates act on adjacent sites.

        Args:
            gates_list (list[BaseOperation]): Logical operation sequence.
                Each operation's targets are logical qubit indices.
            qpu_cfg (dict): QPU configuration with keys ``storage_area``,
                ``operate_area``, ``coupler_map`` and ``readout_error``.
            qbit_num (int): Number of logical qubits.
            optimize (bool, optional): Whether to enable the overlap
                optimization (``execute_with_opt``). Defaults to False.

        Returns:
            tuple[list[BaseOperation], dict]: The mapped operation sequence
            (with MOVE operations and physical qubit targets) and an empty
            final layout dict.
        )");
}
