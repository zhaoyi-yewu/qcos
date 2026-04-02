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

#include "mapping/sabre_mapping.h"

#include <algorithm>

namespace qcos {

std::vector<int> sabre_initial_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list) {
  SABRE sabre(coupling_list);

  // reverse gates
  std::vector<GateOperation> reverse_gates = gates_list;
  std::reverse(reverse_gates.begin(), reverse_gates.end());

  // get initial mapping for reverse ir
  sabre.execute(gates_list);
  std::vector<int> reverse_mapping = sabre.get_logic2phy();

  // get the initial mapping for original ir using reverse mapping
  sabre.execute(reverse_gates, reverse_mapping);
  std::vector<int> mapping = sabre.get_logic2phy();
  return mapping;
}

}  // namespace qcos
