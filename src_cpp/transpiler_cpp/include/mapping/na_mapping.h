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

#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "circuit/base_operation.h"
#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @struct NAQpuConfig
 * @brief Neutral-atom QPU topology configuration.
 *
 * Mirrors the NA-mapping related fields of the Python-side qpu_config.
 * Positions are represented as strings (e.g. "S27", "P100"), matching the
 * Python implementation.
 */
struct NAQpuConfig {
  /// Storage-area position list.
  std::vector<std::string> storage_area;
  /// Operate-area position list.
  std::vector<std::string> operate_area;
  /// Coupler map: gate name -> (endpoint A, endpoint B).
  std::vector<std::pair<std::string, std::pair<std::string, std::string>>>
      coupler_map;
  /// Readout error rate: position -> error value.
  std::unordered_map<std::string, double> readout_error;
};

/**
 * @struct NAGraph
 * @brief Neutral-atom operate-area coupling graph.
 *
 * Contains only edges whose both endpoints lie in the operate_area. Provides
 * adjacency queries and all-source shortest-path distance queries (mirrors
 * networkx's shortest_path_length in the Python implementation).
 */
struct NAGraph {
  /// Adjacency list: position -> set of adjacent positions.
  std::unordered_map<std::string, std::unordered_set<std::string>> adj;
  /// All-source distance table: position -> (position -> shortest-path distance).
  std::unordered_map<std::string, std::unordered_map<std::string, int>>
      shortest_length;

  /// Add an undirected edge.
  void add_edge(const std::string& a, const std::string& b);

  /// Return all neighbors of a position.
  const std::unordered_set<std::string>& neighbors(
      const std::string& p) const;

  /// Check whether two positions are directly adjacent.
  bool is_adjacent(const std::string& a, const std::string& b) const;

  /// Compute all-source shortest-path distances (BFS), filling shortest_length.
  void build_shortest_length();
};

/**
 * @struct NADagNode
 * @brief Dependency-graph node for NA routing.
 *
 * Mirrors a rustworkx DAG node in the Python implementation. A single-qubit
 * node aggregates mergeable consecutive single-qubit gates into its gate list;
 * a two-qubit node holds exactly one gate.
 */
struct NADagNode {
  /// Gates held by the node (multiple for single-qubit nodes, one for multi).
  std::vector<std::shared_ptr<BaseOperation>> gate;
  /// Logical qubits touched by the node.
  std::vector<int> qubits;
  /// Node type: "single" or "multi".
  std::string type;
  /// Index into the original gate sequence.
  int original_idx = -1;
  /// Successor node indices.
  std::vector<int> successors;
  /// Number of unexecuted predecessors.
  int in_degree = 0;
};

/**
 * @class NARoute
 * @brief Abstract base class for neutral-atom mapping/routing strategies.
 *
 * Mirrors the common interface shared by the Python-side NASingleRoute and
 * NARoute. Concrete subclasses (NASingleRoute for single-qubit-only layouts,
 * NADefaultRoute for full MOVE-aware two-qubit routing) implement
 * prepare_data() and execute_with_order(). The default execute_with_opt()
 * falls back to execute_with_order() so that strategies without an overlap
 * optimization (e.g. NASingleRoute) still expose a uniform entry point.
 *
 * Use the free function na_mapping() to obtain a router instance selected by
 * the (na_support_move, na_mapping_type) parameters, analogous to the Python
 * MappingFactory.get_mapper_by_type() dispatch.
 */
class NARoute {
 public:
  virtual ~NARoute() = default;

  /**
   * @brief Configure qpu_config/gates/qbit_num and build the coupling graph.
   */
  virtual void prepare_data(int qbit_num,
                            const std::vector<std::shared_ptr<BaseOperation>>& gates,
                            const NAQpuConfig& qpu_config) = 0;

  /**
   * @brief Iterate over gates and map logical qubits to physical qubits.
   * @return (mapped gate list, final_layout); final_layout is always empty.
   */
  virtual std::pair<std::vector<std::shared_ptr<BaseOperation>>,
                   std::unordered_map<int, int>>
  execute_with_order() = 0;

  /**
   * @brief Execute gates in topological order with simple overlap optimization.
   *
   * The base implementation falls back to execute_with_order() and returns
   * only the mapped gate list; subclasses with a real overlap optimization
   * (e.g. NADefaultRoute) override this.
   *
   * @return The mapped gate list.
   */
  virtual std::vector<std::shared_ptr<BaseOperation>> execute_with_opt();

  /// Logical qubit -> storage-area position.
  std::unordered_map<int, std::string> logical_to_storage;

 protected:
  NAQpuConfig qpu_config_;
  NAGraph ag_;
  std::vector<std::shared_ptr<BaseOperation>> gates_;
  int qbit_num_ = 0;
};

/**
 * @class NASingleRoute
 * @brief Neutral-atom single-qubit routing (single-qubit gates only).
 *
 * Mirrors the Python-side NASingleRoute. Maps logical qubits to the storage
 * area by ascending readout error and emits the gate sequence grouped by qubit.
 * Inherits the common NARoute interface; execute_with_opt() uses the base
 * fallback (equivalent to execute_with_order()).
 */
class NASingleRoute : public NARoute {
 public:
  NASingleRoute() = default;

  /**
   * @brief Configure qpu_config/gates/qbit_num and build the logical-to-storage
   *        mapping.
   */
  void prepare_data(int qbit_num,
                    const std::vector<std::shared_ptr<BaseOperation>>& gates,
                    const NAQpuConfig& qpu_config) override;

  /**
   * @brief Iterate over gates and map logical qubits to physical qubits.
   * @return (mapped gate list, final_layout); final_layout is always empty.
   */
  std::pair<std::vector<std::shared_ptr<BaseOperation>>,
            std::unordered_map<int, int>>
  execute_with_order() override;
};

/**
 * @class NADefaultRoute
 * @brief Neutral-atom routing (single/two-qubit gates + MOVE operations).
 *
 * Mirrors the Python-side NARoute (the "default" na_mapping_type). Moves atoms
 * between the operate area and the storage area so that the two qubits of a
 * two-qubit gate end up on adjacent sites before execution. Supports in-order
 * execution (execute_with_order) and overlap-optimized execution
 * (execute_with_opt).
 */
class NADefaultRoute : public NARoute {
 public:
  NADefaultRoute() = default;

  /**
   * @brief Configure qpu_config/gates/qbit_num and build the coupling graph.
   */
  void prepare_data(int qbit_num,
                    const std::vector<std::shared_ptr<BaseOperation>>& gates,
                    const NAQpuConfig& qpu_config) override;

  /**
   * @brief Execute gates in order, without optimization.
   * @return (mapped gate list, final_layout); final_layout is always empty.
   */
  std::pair<std::vector<std::shared_ptr<BaseOperation>>,
            std::unordered_map<int, int>>
  execute_with_order() override;

  /**
   * @brief Execute gates in topological order with simple overlap optimization.
   * @return The mapped gate list.
   */
  std::vector<std::shared_ptr<BaseOperation>> execute_with_opt() override;

  /**
   * @brief Build the DAG. Returns (DAG node list, measure ops, original-idx ->
   *        DAG-idx mapping).
   */
  std::tuple<std::vector<NADagNode>,
             std::vector<std::shared_ptr<BaseOperation>>,
             std::unordered_map<int, int>>
  get_rx_dag();

  /// Build the initial qubit mapping and mapping tables.
  void get_init_mapping();

  /// Return the currently executable nodes (in-degree == 0).
  std::vector<int> get_front_layer() const;

  /// Find a free position in the operate area for a qubit; empty if none.
  std::string find_pos(int dis) const;

  /// Move a qubit back to the storage area and update the mapping tables.
  void back(const std::string& o);

  /// Move a qubit into the operate area and update the mapping tables.
  void put(int q, const std::string& o);

  /// Move a qubit between two operate-area positions and update the tables.
  void mov(const std::string& o1, const std::string& o2);

  /// Move operate-area qubits that do not belong to the executable gates back
  /// to the storage area.
  void pre_back(const std::vector<NADagNode>& nodes);

  /// Return an empty neighbor of an operate-area position; empty if none.
  std::string get_empty_neighbor(const std::string& p) const;

  /// Return an unlocked neighbor of an operate-area position; empty if none.
  std::string get_unlocked_neighbor(const std::string& p) const;

  /// Move qubit 1 and qubit 2 onto adjacent sites (both already in operate area).
  bool mov_to_neighbors(const std::string& p1, const std::string& p2);

  /// Place q onto a neighbor of p1 (q is in the storage area).
  bool put_to_neighbors1(const std::string& p1, int q);

  /// Place q1 and q2 onto adjacent sites (both in the storage area).
  bool put_to_neighbors2(int q1, int q2);

  /// Execute two-qubit gates.
  void execute_multi_nodes(const std::vector<NADagNode>& nodes);

  /// Place qubits onto suitable operate-area sites before executing two-qubit
  /// gates. Returns the nodes that could not be placed.
  std::vector<NADagNode> mov_multi_nodes(const std::vector<NADagNode>& nodes);

  /// Execute a single-qubit gate.
  void execute_single_node(const NADagNode& node);

  /// Check whether the gate list of nd2 is a suffix of nd1's gate list.
  bool overlap(int nd1, int nd2) const;

  /// Insert a put operation from the overlap step at the proper position.
  std::vector<std::shared_ptr<BaseOperation>> add_put(
      std::vector<std::shared_ptr<BaseOperation>> res,
      std::shared_ptr<BaseOperation> opt);

  /// Adjust the position of put operations; calls add_put to place them.
  void adjust_pos(const std::vector<int>& pos,
                  const std::vector<int>& posq);

  /// Execute a single-qubit gate with overlap optimization.
  void execute_single_node_opt();

  /// Pick an executable node from the current front layer.
  std::pair<int, std::vector<int>> get_max_common();

  /// Logical qubit -> operate-area position (empty string when unmapped).
  std::unordered_map<int, std::string> logical_to_op;
  /// Operate-area position -> logical qubit (-1 when unmapped).
  std::unordered_map<std::string, int> op_to_logical;
  /// Initial mapping (always empty, matching the Python implementation).
  std::unordered_map<int, int> initial_layout;

 private:
  std::vector<NADagNode> dag_;
  std::vector<NADagNode> dag_opt_;
  std::vector<std::shared_ptr<BaseOperation>> measure_;
  std::unordered_map<int, int> node_indices_;
  std::unordered_set<std::string> op_occupied_;
  /// Set of edges with both endpoints free, stored as "min\0max" for ordering
  /// and deduplication.
  std::unordered_set<std::string> free_edges_;
  std::unordered_set<std::string> locked_;
  std::vector<std::shared_ptr<BaseOperation>> res_;
  std::vector<int> front_layer_;
  /// Index of the last executed node (mirrors Python self.pre_node, which was a
  /// node dict; here we use the index and look up node data via dag_).
  int pre_node_idx_ = -1;
  bool has_pre_node_ = false;

  /// Move gate -> (from-position, to-position), carrying position strings
  /// (C++ BaseOperation.arg_value is double and cannot hold strings directly).
  std::unordered_map<BaseOperation*, std::pair<std::string, std::string>>
      move_positions_;

  /// Normalize (a, b) into the ordered pair (min, max).
  static std::pair<std::string, std::string> sorted_edge(const std::string& a,
                                                         const std::string& b);

  /// Encode an ordered pair as a free_edges_ key.
  static std::string edge_key(const std::string& a, const std::string& b);

  /// Parse a free_edges_ key back into an ordered pair.
  static std::pair<std::string, std::string> parse_edge_key(
      const std::string& key);

  /// Create a Move operation and register its position pair.
  std::shared_ptr<BaseOperation> make_move(int q, const std::string& from,
                                           const std::string& to);

  /// Recompute and set each gate's targets / arg_value from logical_to_storage
  /// (mirrors the final logical->physical conversion in the Python impl).
  void finalize_gates(bool deep_copy_layout);

  /// Remove a node from dag_opt_: clears its gates and decrements the in-degree
  /// of its successors (mirrors rustworkx's remove_node).
  void remove_dag_opt_node(int idx);
};

/**
 * @brief Unified neutral-atom mapping entry point (analogous to sabre_routing).
 *
 * Selects a concrete NARoute strategy from the parameters and runs it, so the
 * caller does not need to know the subclass hierarchy. The dispatch mirrors the
 * Python-side MappingFactory.get_mapper_by_type():
 *   - na_support_move == false  -> NASingleRoute (single-qubit-only layout).
 *   - na_support_move == true && na_mapping_type == "default" -> NADefaultRoute
 *     (full two-qubit routing with MOVE shuttling).
 *   - na_support_move == true with any other na_mapping_type is rejected
 *     (ZAC/ZAP are not implemented in the C++ backend yet).
 *
 * @param gates_list Logical operation sequence (targets are logical qubits).
 * @param qpu_config Neutral-atom QPU topology configuration.
 * @param qbit_num Number of logical qubits.
 * @param na_support_move Whether the device supports MOVE + two-qubit gates.
 *        Defaults to false (NASingleRoute).
 * @param na_mapping_type NA mapping algorithm type; only "default" is supported
 *        in C++. Defaults to "default".
 * @param optimize Whether to enable overlap optimization (execute_with_opt);
 *        strategies without one fall back to execute_with_order. Defaults to
 *        false.
 * @return The mapped operation sequence with physical qubit targets (and MOVE
 *         ops inserted when na_support_move is true).
 */
std::vector<std::shared_ptr<BaseOperation>> na_mapping(
    const std::vector<std::shared_ptr<BaseOperation>>& gates_list,
    const NAQpuConfig& qpu_config, int qbit_num, bool na_support_move = false,
    const std::string& na_mapping_type = "default", bool optimize = false);

}  // namespace qcos
