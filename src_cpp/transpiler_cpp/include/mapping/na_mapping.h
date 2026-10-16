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
#include <random>
#include <string>
#include <tuple>
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
 * @class NAZAPRoute
 * @brief Neutral-atom routing via ASAP scheduling + simulated annealing.
 *
 * Mirrors the Python-side NA_ZAP_Route (the "ZAP" na_mapping_type). The
 * pipeline is:
 *   1. scheduling()        — ASAP stage grouping of single/two-qubit gates.
 *   2. sa_mapping_and_placing() — simulated annealing over per-stage qubit
 *      placement that minimizes total atom movement (Manhattan-style distance).
 *   3. routing_asap()      — emit Move ops for atoms whose position changed
 *      between stages, then the gates of each stage; measurements last.
 *
 * Movement cost uses a 20-column grid model (row = id/20, col = id%20), matching
 * the Python implementation. The simulated annealing is deterministic when the
 * caller seeds the RNG (defaults to a fixed seed for reproducibility).
 */
class NAZAPRoute : public NARoute {
 public:
  /// 20-column grid width used by the movement-cost model.
  static constexpr int kGridCols = 20;

  /**
   * @brief Configure qpu_config/gates/qbit_num and build the coupling graph.
   */
  void prepare_data(int qbit_num,
                    const std::vector<std::shared_ptr<BaseOperation>>& gates,
                    const NAQpuConfig& qpu_config) override;

  /**
   * @brief Run scheduling + simulated-annealing placement + routing.
   * @return (mapped gate list, final_layout); final_layout is always empty.
   */
  std::pair<std::vector<std::shared_ptr<BaseOperation>>,
            std::unordered_map<int, int>>
  execute_with_order() override;

  /// Stage i gate list (indices match qubit_scheduling_list_).
  std::vector<std::vector<std::shared_ptr<BaseOperation>>>
      gate_scheduling_list_;
  /// Stage i qubit-id list (the qubits active in stage i).
  std::vector<std::vector<int>> qubit_scheduling_list_;

  /// storage_area_oloc_[stage][pos] = logical qubit id or -1 if free.
  std::vector<std::unordered_map<std::string, int>> storage_area_oloc_;
  /// operate_area_oloc_[stage][pos] = logical qubit id or -1 if free.
  std::vector<std::unordered_map<std::string, int>> operate_area_oloc_;

 private:
  /// Edge list of the operate-area coupling graph (cached for random pick).
  std::vector<std::pair<std::string, std::string>> edges_;
  /// Measurement operations collected during scheduling.
  std::vector<std::shared_ptr<BaseOperation>> measure_;
  /// Result operation list (Move + gates), filled by routing_asap.
  std::vector<std::shared_ptr<BaseOperation>> res_;
  /// RNG; seeded for determinism.
  std::mt19937 rng_{0x5EED1234u};

  /// Per-logical-qubit planned position for each stage.
  using StageMap = std::vector<std::unordered_map<int, std::string>>;

  /// ASAP scheduling: populate gate_scheduling_list_ / qubit_scheduling_list_
  /// and the storage/operate occupancy maps; return collected measures.
  std::vector<std::shared_ptr<BaseOperation>> scheduling();

  /// Manhattan distance on the 20-col grid between two position strings.
  int get_steps(const std::string& posa, const std::string& posb) const;

  /// Total movement cost across all stages of a mapping plan.
  int get_cost(const StageMap& mapping) const;

  /// Cost delta contributed by the affected qubits between adjacent stages.
  int get_affect_cost(const std::vector<int>& affect_qubit_id, int idx,
                       const StageMap& mapping) const;

  /// Pick an unused operate-area coupler edge for the stage; returns (a, b).
  std::pair<std::string, std::string> find_ryd_pos(int stage);
  /// Pick an unused storage-area position for the stage.
  std::string find_pos(int stage);

  /// Fill the initial per-stage placement (readout-error-ranked storage at
  /// stage 0; subsequent stages allocate operate pairs / storage as needed).
  void get_init_mapping_and_placing(StageMap& mapping);

  /// Propose a new mapping by a random local update; records the inverse move
  /// so recover() can undo it. Returns the cost delta.
  int update_mapping(StageMap& mapping);

  /// Undo the last update_mapping move recorded in movement_.
  void recover(StageMap& mapping);

  /// Rebuild storage_area_oloc_ / operate_area_oloc_ from a mapping plan.
  void update_storage_and_operate_area_oloc(const StageMap& mapping);

  /// Post-process: if a qubit stays in storage across two stages, keep the
  /// previous storage position (no move needed).
  StageMap validate_mapping(const StageMap& mapping) const;

  /// Simulated-annealing search for a low-cost mapping plan.
  StageMap sa_mapping_and_placing();

  /// Convert a mapping plan into the Move + gate execution sequence.
  void routing_asap(const StageMap& mapping);

  /// Recorded inverse moves from update_mapping, consumed by recover().
  std::vector<std::tuple<int, int, std::string>> movement_;
};

/**
 * @struct NAMultiQpuConfig
 * @brief Neutral-atom QPU configuration for the "multi" mapping type.
 *
 * Mirrors the grid-coordinate qpu_config used by NAMultiRoute (e.g.
 * hanyuan1_100_new.toml). Positions are plain integers (p = row * column +
 * col), not position strings.
 */
struct NAMultiQpuConfig {
  /// Grid row count.
  int row = 0;
  /// Grid column count.
  int column = 0;
  /// Operate-area position list (already expanded to grid indices).
  std::vector<int> operate_area;
  /// Coupler map: gate name -> (endpoint A, endpoint B) as grid indices.
  std::vector<std::pair<std::string, std::pair<int, int>>> coupler_map;
  /// Readout error: grid index -> error value.
  std::unordered_map<int, double> readout_error;
};

/**
 * @struct IntGraph
 * @brief Simple undirected graph keyed by int nodes.
 *
 * Replaces rustworkx PyGraph for the multi-route algorithm. Provides adjacency
 * queries and edge iteration.
 */
struct IntGraph {
  /// Adjacency list: node -> set of adjacent nodes.
  std::unordered_map<int, std::unordered_set<int>> adj;

  /// Add an undirected edge between a and b.
  void add_edge(int a, int b);

  /// Return all neighbors of node p; empty set if p has no neighbors.
  const std::unordered_set<int>& neighbors(int p) const;

  /// Check whether a and b are directly adjacent.
  bool has_edge(int a, int b) const;

  /// Return all edges as a vector of (a, b) pairs.
  std::vector<std::pair<int, int>> edge_list() const;
};

/**
 * @class NAMultiRoute
 * @brief Neutral-atom multi-route mapping (single-qubit anywhere, two-qubit on
 *        operate-area edges, crosstalk-aware dispersal).
 *
 * Mirrors the Python-side NAMultiRoute (the "multi" na_mapping_type). Adapted
 * for row/column grid-coordinate configurations (e.g.
 * hanyuan1_100_new.toml). Single-qubit gates execute in-place; two-qubit gates
 * require atoms on an operate-area coupler edge, followed by a global cz pulse
 * with inactive atoms dispersed to safe sites.
 */
class NAMultiRoute {
 public:
  NAMultiRoute() = default;

  /**
   * @brief Configure qpu_config/gates/qbit_num and build the operate-area
   *        coupling graph (ag) and the physical grid graph (pg).
   */
  void prepare_data(int qbit_num,
                    const std::vector<std::shared_ptr<BaseOperation>>& gates,
                    const NAMultiQpuConfig& qpu_config);

  /// Build the dependency DAG from the gate list; returns (dag, measure).
  std::pair<std::vector<NADagNode>,
            std::vector<std::shared_ptr<BaseOperation>>>
  get_dg();

  /// Build the initial qubit mapping (subgraph isomorphism + error fallback).
  void get_init_mapping();

  /// Return the currently executable nodes (in-degree == 0).
  std::vector<int> get_front_layer() const;

  /// Return the logical->physical mapping table.
  std::unordered_map<int, int> get_mapping() const;

  /// Check whether a site is safe (no parasitic coupling risk).
  bool is_site_safe(int site,
                    const std::vector<int>& exclude_sites = {}) const;

  /// BFS: find the nearest safe empty site; returns path or empty.
  std::vector<int> find_empty_site(int curr_p,
                                    const std::vector<int>& exclude_sites = {});

  /// BFS: find a path of empty sites from start_p to end_p.
  std::vector<int> get_empty_path(int start_p, int end_p,
                                   const std::vector<int>& exclude_sites = {});

  /// Execute a low-level Move and update mapping tables.
  void do_move(int q, const std::vector<int>& path);

  /// Move qubit q to target_p (with eviction and pathfinding).
  void move_qubit(int q, int target_p);

  /// Execute single-qubit gate nodes in-place.
  void execute_single_nodes(const std::vector<int>& nodes);

  /// Find the lowest-cost operate-area edge for q1, q2.
  std::pair<int, int> find_best_operate_edge(
      int q1, int q2, const std::unordered_set<int>& exclude_nodes = {}) const;

  /// Disperse inactive qubits before a global pulse.
  void disperse_inactive_qubits(
      const std::vector<std::pair<int, int>>& active_edges);

  /// Execute two-qubit gate nodes (supports parallel, global cz pulse).
  void execute_multi_nodes(const std::vector<int>& nodes);

  /**
   * @brief Execute gates in topological order: single-qubit in-place,
   *        two-qubit moved to operate edges then global cz pulse.
   * @return (mapped gate list, final_mapping).
   */
  std::pair<std::vector<std::shared_ptr<BaseOperation>>,
            std::unordered_map<int, int>>
  execute_with_order();

  /// Grid row count.
  int rows_ = 0;
  /// Grid column count.
  int cols_ = 0;
  /// Operate-area positions (grid indices).
  std::vector<int> operate_area_;
  /// All sites (= operate_area_).
  std::vector<int> all_sites_;
  /// Initial layout (logical -> physical).
  std::unordered_map<int, int> initial_layout;
  /// Final mapping (logical -> physical).
  std::unordered_map<int, int> final_mapping;

 private:
  NAMultiQpuConfig qpu_config_;
  IntGraph ag_;
  IntGraph pg_;
  /// Grid index -> ag node index.
  std::unordered_map<int, int> ag_val_to_idx_;
  std::vector<std::shared_ptr<BaseOperation>> gates_;
  int qbit_num_ = 0;

  std::vector<NADagNode> dg_;
  std::vector<NADagNode> dg_opt_;
  std::vector<std::shared_ptr<BaseOperation>> measure_;
  std::vector<std::shared_ptr<BaseOperation>> res_;

  /// Logical qubit -> physical position (-1 = unmapped).
  std::unordered_map<int, int> q_to_p_;
  /// Physical position -> logical qubit (-1 = empty).
  std::unordered_map<int, int> p_to_q_;

  /// Remove a node from dg_opt_: decrements successors' in_degree, marks removed.
  void remove_dag_opt_node(int idx);

  /// Recursive backtracking subgraph-isomorphism helper (VF2-lite).
  bool try_subgraph_match(
      const IntGraph& host, const IntGraph& pattern,
      const std::vector<int>& pattern_nodes,
      const std::vector<std::pair<int, int>>& pattern_edges,
      std::unordered_map<int, int>& mapping,
      std::unordered_set<int>& used_host) const;
};

/**
 * @brief Unified neutral-atom mapping entry point for the "multi" type.
 *
 * Creates a NAMultiRoute, runs prepare_data + execute_with_order, and returns
 * the mapped operation sequence.
 *
 * @param gates_list Logical operation sequence (targets are logical qubits).
 * @param qpu_config Grid-coordinate QPU configuration.
 * @param qbit_num Number of logical qubits.
 * @return The mapped operation sequence with MOVE ops and physical qubit
 *         targets.
 */
std::vector<std::shared_ptr<BaseOperation>> na_multi_mapping(
    const std::vector<std::shared_ptr<BaseOperation>>& gates_list,
    const NAMultiQpuConfig& qpu_config, int qbit_num);

/**
 * @brief Unified neutral-atom mapping entry point (analogous to sabre_routing).
 *
 * Selects a concrete NARoute strategy from the parameters and runs it, so the
 * caller does not need to know the subclass hierarchy. The dispatch mirrors the
 * Python-side MappingFactory.get_mapper_by_type():
 *   - na_support_move == false  -> NASingleRoute (single-qubit-only layout).
 *   - na_support_move == true && na_mapping_type == "default" -> NADefaultRoute
 *     (full two-qubit routing with MOVE shuttling).
 *   - na_support_move == true && na_mapping_type == "ZAP" -> NAZAPRoute
 *     (ASAP scheduling + simulated annealing, MOVE shuttling).
 *
 * @param gates_list Logical operation sequence (targets are logical qubits).
 * @param qpu_config Neutral-atom QPU topology configuration.
 * @param qbit_num Number of logical qubits.
 * @param na_support_move Whether the device supports MOVE + two-qubit gates.
 *        Defaults to false (NASingleRoute).
 * @param na_mapping_type NA mapping algorithm type; "default" or "ZAP" are
 *        supported in C++. Defaults to "default".
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
