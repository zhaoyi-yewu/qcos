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

#include "mapping/chip_data.h"

#include <algorithm>
#include <fstream>
#include <queue>
#include <regex>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace qcos {

namespace {

/**
 * @brief 解析 CSV 文本，返回二维字符串表格
 *
 * @param content CSV 原始文本
 * @return 解析后的行-列字符串结构
 */
std::vector<std::vector<std::string>> parse_csv(const std::string& content) {
  std::vector<std::vector<std::string>> rows;
  std::vector<std::string> current_row;
  std::string current_field;
  // 是否正处于引号包裹的字段内
  bool in_quotes = false;

  for (size_t i = 0; i < content.size(); ++i) {
    char ch = content[i];

    if (in_quotes) {
      if (ch == '"') {
        // 连续两个双引号是 CSV 的转义写法，解析为一个字面引号
        if (i + 1 < content.size() && content[i + 1] == '"') {
          current_field += '"';
          ++i;
        } else {
          // 单个双引号结束引号字段
          in_quotes = false;
        }
      } else {
        current_field += ch;
      }
    } else {
      if (ch == '"') {
        // 进入引号字段
        in_quotes = true;
      } else if (ch == ',') {
        // 逗号分隔符：提交当前字段，开始下一个
        current_row.push_back(std::move(current_field));
        current_field.clear();
      } else if (ch == '\n' || ch == '\r') {
        // 处理 CRLF 换行：跳过紧跟 '\r' 的 '\n'
        if (ch == '\r' && i + 1 < content.size() && content[i + 1] == '\n') {
          ++i;
        }
        // 换行：提交当前字段和当前行
        current_row.push_back(std::move(current_field));
        current_field.clear();
        // 跳过空行（防止连续换行产生空行记录）
        if (!current_row.empty()) {
          rows.push_back(std::move(current_row));
          current_row.clear();
        }
      } else {
        current_field += ch;
      }
    }
  }

  // 处理末尾没有换行的最后一个字段/行
  if (!current_field.empty() || !current_row.empty()) {
    current_row.push_back(std::move(current_field));
    rows.push_back(std::move(current_row));
  }

  return rows;
}

/**
 * @brief 解析 CZ 保真度字段，提取有向边及对应保真度
 *
 * 字段格式示例: "0_1: 0.993, 2_3: 0.981"
 * 每个匹配项形如 <source>_<target>: <fidelity>，解析失败时跳过该条目。
 *
 * @param field CSV 中第 6 列的 CZ 保真度原始字符串
 * @param[out] edges 解析得到的有向边列表，与 fidelities 对应
 * @param[out] fidelities 解析得到的保真度列表，与 edges 对应
 */
void parse_cz_fidelity_field(const std::string& field,
                             std::vector<std::pair<int, int>>& edges,
                             std::vector<double>& fidelities) {
  // 正则匹配 "源位_目标位: 保真度" 模式，如 "0_1: 0.993"
  static const std::regex edge_pattern(R"((\d+)_(\d+)\s*:\s*([0-9.]+))");
  auto match_begin =
      std::sregex_iterator(field.begin(), field.end(), edge_pattern);
  auto match_end = std::sregex_iterator();

  for (auto it = match_begin; it != match_end; ++it) {
    try {
      int source = std::stoi((*it)[1].str());
      int target = std::stoi((*it)[2].str());
      double fidelity = std::stod((*it)[3].str());
      edges.emplace_back(source, target);
      fidelities.push_back(fidelity);
    } catch (...) {
      // 数值转换失败时跳过该条边，不影响其余数据
      continue;
    }
  }
}

}  // namespace

ChipCalibration load_chip_calibration(const std::string& csv_path) {
  std::ifstream file(csv_path);
  if (!file.is_open()) {
    throw std::runtime_error("无法打开标定文件: " + csv_path);
  }

  // 一次性读入整个文件内容，避免逐行 I/O
  std::string content((std::istreambuf_iterator<char>(file)),
                      std::istreambuf_iterator<char>());
  auto rows = parse_csv(content);

  std::vector<std::pair<int, int>> coupling_list;
  std::vector<double> edge_fidelities;
  // 用 map 暂存单比特保真度，最后按原始 ID 直接写入 vector
  std::unordered_map<int, double> fidelity_by_qubit;
  // 跟踪最大量子位 ID，用于分配 vector 大小
  int max_qubit_id = -1;

  // 从第 2 行开始（跳过表头）
  for (size_t row_idx = 1; row_idx < rows.size(); ++row_idx) {
    const auto& row = rows[row_idx];
    // 每行至少需要 6 列：ID, ..., 单比特保真度, CZ 保真度字段
    if (row.size() < 6) continue;

    int qubit_id = -1;
    try {
      // 第 1 列：物理量子位 ID
      qubit_id = std::stoi(row[0]);
    } catch (...) {
      // ID 解析失败则跳过整行
      continue;
    }
    // 忽略无效 ID
    if (qubit_id < 0) continue;
    max_qubit_id = std::max(max_qubit_id, qubit_id);

    double single_qubit_fid = 0.0;
    try {
      // 第 5 列：单比特门保真度
      single_qubit_fid = std::stod(row[4]);
    } catch (...) {
      // 解析失败默认为 0，表示无标定数据
      single_qubit_fid = 0.0;
    }
    fidelity_by_qubit[qubit_id] = single_qubit_fid;

    // 第 6 列：CZ 边保真度，格式如 "0_1: 0.99, 2_3: 0.98"
    std::vector<std::pair<int, int>> row_edges;
    std::vector<double> row_fidelities;
    parse_cz_fidelity_field(row[5], row_edges, row_fidelities);

    // 将本行的耦合边追加到全局列表，并同步更新 max_qubit_id
    for (size_t edge_idx = 0; edge_idx < row_edges.size(); ++edge_idx) {
      coupling_list.push_back(row_edges[edge_idx]);
      edge_fidelities.push_back(row_fidelities[edge_idx]);
      // 边的端点 ID 可能大于当前行的量子位 ID
      max_qubit_id = std::max({max_qubit_id, row_edges[edge_idx].first,
                               row_edges[edge_idx].second});
    }
  }

  // 将 map 暂存的单比特保真度写入按原始 ID 直接索引的 vector
  std::vector<double> single_qubit_fidelities;
  if (max_qubit_id >= 0) {
    single_qubit_fidelities.assign(max_qubit_id + 1, 0.0);
    for (const auto& [qubit_id, fidelity] : fidelity_by_qubit) {
      single_qubit_fidelities[qubit_id] = fidelity;
    }
  }

  return ChipCalibration(std::move(coupling_list), std::move(edge_fidelities),
                         std::move(single_qubit_fidelities));
}

}  // namespace qcos
