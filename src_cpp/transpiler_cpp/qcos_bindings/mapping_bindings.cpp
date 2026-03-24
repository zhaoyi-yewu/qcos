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
            SABRE constructor.

            Args:
                coupling_list (List[Tuple[int,int]]): Physical qubit connectivity.
                extention_size (int, optional): Lookahead set size. Default is 20.
                weight (float, optional): Front layer / lookahead weight. Default is 0.5.
                decay (float, optional): SWAP decay coefficient. Default is 0.001.
            )pbdoc")

      .def("execute",
           static_cast<void (SABRE::*)(const std::vector<GateOperation>&,
                                       const std::vector<int>&)>(
               &SABRE::execute),
           py::arg("gates_list"), py::arg("initial_l2p") = std::vector<int>{},
           R"pbdoc(
            Execute SABRE routing.

            Args:
                gates_list (List[GateOperation]):
                    Logical gate sequence.
                initial_l2p (List[int], optional):
                    Initial logical-to-physical mapping. Defaults to empty.

            Returns:
                None
            )pbdoc")

      .def("get_physical_gates", &SABRE::get_physical_gates,
           R"pbdoc(
            Get the sequence of mapped physical gates after routing.

            Returns:
                List[GateOperation]: The physical gate sequence.
            )pbdoc");
}