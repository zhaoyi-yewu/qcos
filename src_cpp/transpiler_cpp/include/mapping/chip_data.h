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

#pragma once

#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace qcos {

/**
 * @brief 芯片标定数据
 *
 * 封装量子芯片的耦合映射(coupling map)、边保真度和单比特保真度。
 * 构造时校验 coupling_list 和 edge_fidelities 等长, 把运行时不变量提到构造期。
 */
struct ChipCalibration {
  std::vector<std::pair<int, int>> coupling_list;  ///< 有向耦合边列表
  std::vector<double>
      edge_fidelities;  ///< 与 coupling_list 对应的 CZ 门保真度
  std::vector<double>
      single_qubit_fidelities;  ///< 单比特门保真度, 按物理位 ID 直接索引

  ChipCalibration() = default;

  /**
   * @brief 构造芯片标定数据
   * @param coupling_list 有向耦合边列表
   * @param edge_fidelities 边保真度, 必须与 coupling_list 等长
   * @param single_qubit_fidelities 单比特保真度, 按物理位 ID 直接索引
   * @throw std::invalid_argument 当 coupling_list.size() !=
   * edge_fidelities.size()
   */
  ChipCalibration(std::vector<std::pair<int, int>> coupling_list,
                  std::vector<double> edge_fidelities,
                  std::vector<double> single_qubit_fidelities)
      : coupling_list(std::move(coupling_list)),
        edge_fidelities(std::move(edge_fidelities)),
        single_qubit_fidelities(std::move(single_qubit_fidelities)) {
    if (this->coupling_list.size() != this->edge_fidelities.size()) {
      throw std::invalid_argument(
          "ChipCalibration: coupling_list size (" +
          std::to_string(this->coupling_list.size()) +
          ") != edge_fidelities size (" +
          std::to_string(this->edge_fidelities.size()) + ")");
    }
  }
};

/**
 * @brief 从北量院标定 CSV 文件加载芯片标定数据
 *
 * @param csv_path 标定 CSV 文件路径
 * @return ChipCalibration 芯片标定数据
 */
ChipCalibration load_chip_calibration(const std::string& csv_path);

}  // namespace qcos
