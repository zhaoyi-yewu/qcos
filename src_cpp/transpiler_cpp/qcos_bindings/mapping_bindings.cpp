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

#include <stdexcept>

#include "circuit/gate_operation.h"
#include "mapping/greedy_routing.h"
#include "mapping/sabre_mapping.h"
#include "mapping/sabre_routing.h"

namespace py = pybind11;
using namespace qcos;

namespace {

/**
 * @brief 绑定 high_performance.sabre_routing 的 C++ BaseOperation 入口。
 *
 * @param gates_list_raw Python 侧传入的 BaseOperation 对象列表。
 * @param coupling_list 物理耦合图边列表。
 * @param initial_l2p 初始逻辑到物理映射。
 * @param extension_size 扩展集大小。
 * @param weight 前沿层与扩展层成本权重。
 * @param decay SWAP 衰减系数。
 * @return py::list 路由后的 BaseOperation 对象列表。
 */
py::list bind_cpp_sabre_routing(
    const std::vector<qcos::BaseOperation*>& gates_list_raw,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<int>& initial_l2p, int extension_size, double weight,
    double decay) {
  std::vector<std::shared_ptr<qcos::BaseOperation>> gates_list;
  gates_list.reserve(gates_list_raw.size());
  for (auto* op : gates_list_raw) {
    if (op == nullptr) {
      throw std::invalid_argument(
          "sabre_routing received a null BaseOperation");
    }
    gates_list.push_back(op->clone());
  }

  auto routed_ops = qcos::sabre_routing(gates_list, coupling_list, initial_l2p,
                                        extension_size, weight, decay);

  py::list py_list;
  for (auto& op : routed_ops) {
    py_list.append(std::move(op));
  }
  return py_list;
}

}  // namespace

void bind_mapping(py::module_& m) {
  py::class_<SABRE>(m, "SABRE", "SABRE quantum routing algorithm")
      .def(py::init<const std::vector<std::pair<int, int>>&, int, double,
                    double>(),
           py::arg("coupling_list"), py::arg("extension_size") = 20,
           py::arg("weight") = 0.5, py::arg("decay") = 0.001,
           R"pbdoc(
Construct a SABRE router.

Args:
    coupling_list (list[tuple[int, int]]): Physical qubit connectivity
        graph.
    extension_size (int, optional): Size of the lookahead set.
        Defaults to 20.
    weight (float, optional): Weight between front layer and lookahead
        cost. Defaults to 0.5.
    decay (float, optional): SWAP decay coefficient. Defaults to 0.001.
)pbdoc")

      .def("execute",
           static_cast<void (SABRE::*)(const std::vector<GateOperation>&,
                                       const std::vector<int>&)>(
               &SABRE::execute),
           py::arg("gates_list"), py::arg("initial_l2p") = std::vector<int>{},
           R"pbdoc(
Execute SABRE routing.

Args:
    gates_list (list[GateOperation]): Logical gate sequence.
    initial_l2p (list[int], optional): Initial logical-to-physical
        mapping. Defaults to empty.

Returns:
    None
)pbdoc")

      .def("get_logic2phy", &SABRE::get_logic2phy,
           R"pbdoc(
Get the final logical-to-physical mapping after routing.

Returns:
    list[int]: The index is logical qubit and value is physical qubit.
)pbdoc")

      .def("get_physical_gates", &SABRE::get_physical_gates,
           R"pbdoc(
Get the sequence of mapped physical gates after routing.

Returns:
    list[GateOperation]: The physical gate sequence.
)pbdoc");

  py::class_<GreedyRouting>(
      m, "GreedyRouting",
      "Greedy blocked-gate routing: insert a SWAP only when a gate is blocked")
      .def(py::init<const std::vector<std::pair<int, int>>&>(),
           py::arg("coupling_list"))
      .def("execute",
           static_cast<void (GreedyRouting::*)(
               const std::vector<GateOperation>&, const std::vector<int>&)>(
               &GreedyRouting::execute),
           py::arg("gates_list"), py::arg("initial_l2p") = std::vector<int>{})
      .def("get_physical_gates", &GreedyRouting::get_physical_gates)
      .def_readonly("logic2phy", &GreedyRouting::logic2phy)
      .def_readonly("phy2logic", &GreedyRouting::phy2logic);

  m.def("sabre_initial_mapping",
        static_cast<std::vector<int> (*)(
            const std::vector<qcos::GateOperation>&,
            const std::vector<std::pair<int, int>>&)>(
            &qcos::sabre_initial_mapping),
        py::arg("gates_list"), py::arg("coupling_list"),
        R"pbdoc(
Get the initial mapping using the SABRE algorithm.

Args:
    gates_list (list[GateOperation]): Logical gate sequence.
    coupling_list (list[tuple[int, int]]): Physical qubit coupling list.

Returns:
    list[int]: The initial logical-to-physical mapping.
)pbdoc");

  m.def("sabre_routing", &bind_cpp_sabre_routing, py::arg("gates_list"),
        py::arg("coupling_list"), py::arg("initial_l2p") = std::vector<int>{},
        py::arg("extension_size") = 20, py::arg("weight") = 0.5,
        py::arg("decay") = 0.001,
        R"pbdoc(
Execute SABRE routing.

Args:
    gates_list (list[BaseOperation]): Logical operation sequence.
    coupling_list (list[tuple[int, int]]): Physical qubit coupling list.
    initial_l2p (list[int], optional): Initial logical-to-physical mapping.
        When empty, SABRE computes the initial mapping internally.
        Defaults to empty.
    extension_size (int, optional): Size of the lookahead set.
        Defaults to 20.
    weight (float, optional): Weight between front layer and lookahead cost.
        Defaults to 0.5.
    decay (float, optional): SWAP decay coefficient. Defaults to 0.001.

Returns:
    list[BaseOperation]: The routed physical operation sequence.
)pbdoc");
}