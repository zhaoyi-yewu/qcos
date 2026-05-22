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

#include "circuit/gate_operation.h"
#include "mapping/greedy_routing.h"
#include "mapping/sabre_mapping.h"
#include "mapping/sabre_routing.h"

namespace py = pybind11;
using namespace qcos;

void bind_mapping(py::module_& m) {
  py::class_<SABRE>(m, "SABRE", "SABRE quantum routing algorithm")
      .def(py::init<const std::vector<std::pair<int, int>>&, int, double,
                    double>(),
           py::arg("coupling_list"), py::arg("extention_size") = 20,
           py::arg("weight") = 0.5, py::arg("decay") = 0.001,
           R"pbdoc(
Construct a SABRE router.

Args:
    coupling_list (list[tuple[int, int]]): Physical qubit connectivity
        graph.
    extention_size (int, optional): Size of the lookahead set.
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

  m.def("sabre_routing", &qcos::sabre_routing, py::arg("gates_list"),
        py::arg("coupling_list"), py::arg("initial_l2p") = std::vector<int>{},
        py::arg("extention_size") = 20, py::arg("weight") = 0.5,
        py::arg("decay") = 0.001,
        R"pbdoc(
Execute SABRE routing.

Args:
    gates_list (list[GateOperation]): Logical gate sequence.
    coupling_list (list[tuple[int, int]]): Physical qubit coupling list.
    initial_l2p (list[int], optional): Initial logical-to-physical mapping.
        When empty, SABRE computes the initial mapping internally.
        Defaults to empty.
    extention_size (int, optional): Size of the lookahead set.
        Defaults to 20.
    weight (float, optional): Weight between front layer and lookahead cost.
        Defaults to 0.5.
    decay (float, optional): SWAP decay coefficient. Defaults to 0.001.

Returns:
    list[GateOperation]: The routed physical gate sequence.
)pbdoc");
}