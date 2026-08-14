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
#include <nanobind/stl/vector.h>

#include "verify/cmss_verifier.h"
#include "verify/qpu_verifier.h"
#include "verify/quafu_verifier.h"

namespace nb = nanobind;
using namespace qcos;

void bind_verify(nb::module_& m) {
  nb::class_<VerifyParams>(
      m, "VerifyParams",
      "Verification parameters, populated by Python from the API request.")
      .def(nb::init<>())
      .def_rw("bits", &VerifyParams::bits)
      .def_rw("basis_gates", &VerifyParams::basis_gates)
      .def_rw("coupling_list", &VerifyParams::coupling_list)
      .def_rw("edge_fidelities", &VerifyParams::edge_fidelities)
      .def_rw("single_qubit_fidelities",
              &VerifyParams::single_qubit_fidelities)
      .def_rw("target_bits", &VerifyParams::target_bits);

  nb::class_<VerifyResult>(m, "VerifyResult",
                           "Verification result with pass/fail status and "
                           "failure messages.")
      .def(nb::init<>())
      .def_ro("passed", &VerifyResult::passed)
      .def_ro("message", &VerifyResult::message);

  nb::class_<QuafuVerifier>(m, "QuafuVerifier",
                            "Quafu (夸父) superconducting chip verifier.")
      .def(nb::init<const VerifyParams&>(), nb::arg("params"))
      .def(
          "verify",
          [](const QuafuVerifier& self, const std::string& qasm_string,
             bool verbose) {
            nb::gil_scoped_release release;
            return self.verify(qasm_string, verbose);
          },
          nb::arg("qasm_string"), nb::arg("verbose") = false,
          R"(
Verify whether a circuit can execute on the Quafu chip.

Args:
    qasm_string (str): OpenQASM 2.0 circuit source.
    verbose (bool): If True, print failure message to stdout.

Returns:
    VerifyResult: Result with passed (bool) and message (str).
          )");

  nb::class_<CMSSVerifier>(m, "CMSSVerifier",
                           "CMSS (compilation service) verifier.")
      .def(nb::init<const VerifyParams&>(), nb::arg("params"))
      .def(
          "verify",
          [](const CMSSVerifier& self, const std::string& qasm_string,
             bool verbose) {
            nb::gil_scoped_release release;
            return self.verify(qasm_string, verbose);
          },
          nb::arg("qasm_string"), nb::arg("verbose") = false,
          R"(
Verify whether a circuit can execute for CMSS.

Args:
    qasm_string (str): OpenQASM 2.0 circuit source.
    verbose (bool): If True, print failure message to stdout.

Returns:
    VerifyResult: Result with passed (bool) and message (str).
          )");
}
