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

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <unordered_map>
#include <utility>

#include "mapping/mcts_routing.h"

namespace py = pybind11;

namespace {

qcos::MCTSArchitectureGraph parse_architecture_graph(const py::object& ag) {
  qcos::MCTSArchitectureGraph graph;
  for (auto node_obj : ag.attr("nodes")) {
    graph.nodes.push_back(py::cast<int>(node_obj));
  }
  for (auto edge_obj : ag.attr("edges")) {
    graph.edges.push_back(py::cast<std::pair<int, int>>(edge_obj));
  }
  return graph;
}

qcos::MCTSDependencyGraph parse_dependency_graph(const py::object& dg_py) {
  qcos::MCTSDependencyGraph dg;
  auto node_view = dg_py.attr("nodes");
  for (auto node_obj : node_view) {
    const int node_id = py::cast<int>(node_obj);
    py::object data_obj = node_view.attr("__getitem__")(node_obj);

    qcos::MCTSDGNode info;
    info.id = node_id;
    info.qubits =
        py::cast<std::vector<int>>(data_obj.attr("__getitem__")("qubits"));
    info.num_gate_2q =
        py::cast<int>(data_obj.attr("__getitem__")("num_gate_2q"));

    py::list gates_list = py::cast<py::list>(data_obj.attr("__getitem__")("gates"));
    for (auto gate_obj : gates_list) {
      py::tuple gate_tuple = py::cast<py::tuple>(gate_obj);
      qcos::MCTSGateSpec gate;
      gate.name = py::cast<std::string>(gate_tuple[0]);
      gate.qubits = py::cast<std::vector<int>>(gate_tuple[1]);
      gate.params = py::cast<std::vector<double>>(gate_tuple[2]);
      info.gates.push_back(std::move(gate));
    }

    for (auto succ_obj : dg_py.attr("successors")(node_id)) {
      info.successors.push_back(py::cast<int>(succ_obj));
    }
    for (auto pred_obj : dg_py.attr("predecessors")(node_id)) {
      info.predecessors.push_back(py::cast<int>(pred_obj));
    }
    dg.nodes[node_id] = std::move(info);
  }

  dg.num_q_log = py::cast<int>(dg_py.attr("num_q_log"));
  return dg;
}

qcos::MCTSSearchConfig parse_search_config(const py::object& search_tree) {
  qcos::MCTSSearchConfig config;
  config.dg = parse_dependency_graph(search_tree.attr("DG"));
  config.objective = py::cast<std::string>(search_tree.attr("objective"));

  auto select_mode = py::cast<py::list>(search_tree.attr("select_mode"));
  config.select_mode_name = py::cast<std::string>(select_mode[0]);
  config.select_mode_param = py::cast<double>(select_mode[1]);

  auto mode_bp = py::cast<py::list>(search_tree.attr("mode_BP"));
  config.mode_bp_name = py::cast<std::string>(mode_bp[0]);

  auto mode_decision = py::cast<py::list>(search_tree.attr("mode_decision"));
  config.mode_decision_name = py::cast<std::string>(mode_decision[0]);

  auto mode_sim = py::cast<py::list>(search_tree.attr("mode_sim"));
  config.mode_sim_name = py::cast<std::string>(mode_sim[0]);
  auto mode_sim_args = py::cast<py::list>(mode_sim[1]);
  config.mode_sim_times = py::cast<int>(mode_sim_args[0]);
  config.mode_sim_num_cx = py::cast<int>(mode_sim_args[1]);

  config.score_layer = py::cast<int>(search_tree.attr("score_layer"));
  config.use_prune = py::cast<bool>(search_tree.attr("use_prune"));
  config.use_hash = py::cast<bool>(search_tree.attr("use_hash"));
  config.init_mapping = py::cast<std::vector<int>>(search_tree.attr("init_mapping"));
  config.score_decay_rate_size =
      py::cast<double>(search_tree.attr("score_decay_rate_size"));
  config.score_decay_rate_depth =
      py::cast<double>(search_tree.attr("score_decay_rate_depth"));
  return config;
}

std::unordered_map<int, int> parse_initial_layout(const py::dict& initial_layout) {
  std::unordered_map<int, int> result;
  for (auto item : initial_layout) {
    result.emplace(py::cast<int>(item.first), py::cast<int>(item.second));
  }
  return result;
}

py::tuple execute_routing_py(qcos::CppMCTSRouting& router,
                             const py::object& search_tree,
                             const py::object& ag,
                             const py::dict& initial_layout,
                             int num_q_vir,
                             const py::list& measure_ops) {
  const auto search_config = parse_search_config(search_tree);
  const auto architecture_graph = parse_architecture_graph(ag);
  const auto layout = parse_initial_layout(initial_layout);

  qcos::MCTSRoutingResult result;
  {
    py::gil_scoped_release release;
    result = router.execute_routing(search_config, architecture_graph, layout,
                                    num_q_vir);
  }

  py::module_ gate_module =
      py::module_::import("wy_qcos.common.cmss.gate_operation");
  py::object create_gate = gate_module.attr("create_gate");

  py::list mapped_ir;
  for (const auto& gate : result.mapped_ir) {
    mapped_ir.append(create_gate(gate.name, gate.qubits, gate.params));
  }

  py::dict mapping_virtual_to_final;
  for (const auto& [logical, physical] : result.mapping_virtual_to_final) {
    mapping_virtual_to_final[py::int_(logical)] = py::int_(physical);
  }

  for (auto gate_obj : measure_ops) {
    py::object gate = py::reinterpret_borrow<py::object>(gate_obj);
    py::list new_targets;
    for (auto target_obj : gate.attr("targets")) {
      const int q = py::cast<int>(target_obj);
      auto it = result.mapping_virtual_to_final.find(q);
      if (it != result.mapping_virtual_to_final.end()) {
        new_targets.append(py::int_(it->second));
      } else {
        new_targets.append(py::int_(q));
      }
    }
    gate.attr("targets") = new_targets;
    mapped_ir.append(gate);
  }

  return py::make_tuple(mapped_ir, mapping_virtual_to_final);
}

}  // namespace

void bind_cpp_mcts(py::module_& m) {
  py::class_<qcos::CppMCTSRouting>(m, "CppMCTSRouting",
                                   "C++ implementation of MCTS routing")
      .def(py::init<int>(), py::arg("selec_times") = 5)
      .def_property("selec_times", &qcos::CppMCTSRouting::selec_times,
                    &qcos::CppMCTSRouting::set_selec_times)
      .def("execute_routing", &execute_routing_py, py::arg("search_tree"),
           py::arg("ag"), py::arg("initial_layout"), py::arg("num_q_vir"),
           py::arg("measure_ops"));
}
