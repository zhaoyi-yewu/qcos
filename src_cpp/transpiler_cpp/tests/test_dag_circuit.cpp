/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <memory>
#include <set>
#include <string>
#include <tuple>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/dag_node.h"
#include "circuit/gate_operation.h"
#include "circuit/quantum_circuit.h"

using namespace qcos;

namespace {

constexpr double kPi = 3.14159265358979323846;

std::shared_ptr<BaseOperation> make_gate(const std::string& name,
                                         const std::vector<int>& targets,
                                         const std::vector<double>& args = {},
                                         bool allow_undefined = false) {
  return std::shared_ptr<BaseOperation>(
      create_gate(name, targets, args, allow_undefined));
}

std::vector<std::vector<std::string>> normalize_run_signatures(
    const std::set<std::vector<DAGNode*>>& runs) {
  std::vector<std::vector<std::string>> normalized;
  normalized.reserve(runs.size());
  for (const auto& run : runs) {
    std::vector<std::string> signature;
    signature.reserve(run.size());
    for (const auto& node : run) {
      auto* op = dynamic_cast<DAGOpNode*>(node);
      std::string entry = op->name() + "[";
      for (size_t index = 0; index < op->qargs.size(); ++index) {
        if (index > 0) {
          entry += ",";
        }
        entry += std::to_string(op->qargs[index]);
      }
      entry += "]";
      signature.push_back(std::move(entry));
    }
    normalized.push_back(std::move(signature));
  }
  std::sort(normalized.begin(), normalized.end(),
            [](const auto& lhs, const auto& rhs) {
              if (lhs.size() != rhs.size()) {
                return lhs.size() < rhs.size();
              }
              return lhs < rhs;
            });
  return normalized;
}

std::vector<int> node_ids(const std::vector<DAGNode*>& nodes) {
  std::vector<int> ids;
  ids.reserve(nodes.size());
  for (const auto& node : nodes) {
    ids.push_back(node->node_id());
  }
  return ids;
}

std::vector<std::string> node_labels(const std::vector<DAGNode*>& nodes) {
  std::vector<std::string> labels;
  labels.reserve(nodes.size());
  for (const auto& node : nodes) {
    if (dynamic_cast<DAGInNode*>(node)) {
      labels.push_back("in");
      continue;
    }
    if (dynamic_cast<DAGOutNode*>(node)) {
      labels.push_back("out");
      continue;
    }
    labels.push_back(dynamic_cast<DAGOpNode*>(node)->name());
  }
  return labels;
}

std::vector<std::string> op_names(const std::vector<DAGOpNode*>& nodes) {
  std::vector<std::string> labels;
  labels.reserve(nodes.size());
  for (const auto& node : nodes) {
    labels.push_back(node->name());
  }
  return labels;
}

std::string qargs_signature(const std::vector<int>& qargs) {
  std::string signature = "[";
  for (size_t index = 0; index < qargs.size(); ++index) {
    if (index > 0) {
      signature += ",";
    }
    signature += std::to_string(qargs[index]);
  }
  signature += "]";
  return signature;
}

std::string node_signature(DAGNode* node) {
  if (auto* in = dynamic_cast<DAGInNode*>(node)) {
    return "in[" + std::to_string(in->wire()) + "]";
  }
  if (auto* out = dynamic_cast<DAGOutNode*>(node)) {
    return "out[" + std::to_string(out->wire()) + "]";
  }
  auto* op = dynamic_cast<DAGOpNode*>(node);
  return op->name() + qargs_signature(op->qargs);
}

std::vector<std::tuple<std::string, std::string, int>>
normalize_edge_signatures(const std::vector<DAGCircuit::EdgeTriple>& edges) {
  std::vector<std::tuple<std::string, std::string, int>> normalized;
  normalized.reserve(edges.size());
  for (const auto& edge : edges) {
    normalized.emplace_back(node_signature(edge.src), node_signature(edge.dst),
                            edge.wire);
  }
  std::sort(normalized.begin(), normalized.end());
  return normalized;
}

bool contains_node_id(const std::set<DAGNode*>& nodes, int node_id) {
  for (const auto& node : nodes) {
    if (node && node->node_id() == node_id) {
      return true;
    }
  }
  return false;
}

DAGCircuit build_five_qubit_chain() {
  DAGCircuit dag;
  dag.add_qubits(5);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("cx", {1, 2}));
  dag.apply_operation_back(make_gate("cx", {2, 3}));
  dag.apply_operation_back(make_gate("cx", {3, 4}));
  dag.apply_operation_back(make_gate("h", {4}));
  return dag;
}

}  // namespace

TEST(DAGCircuitTest, AddQubits) {
  DAGCircuit dag;
  dag.add_qubits(3);
  EXPECT_EQ(dag.get_input_map().size(), 3u);
  EXPECT_EQ(dag.get_output_map().size(), 3u);
  EXPECT_EQ(dag.get_multi_graph().num_nodes(), 6);
}

TEST(DAGCircuitTest, ApplyOperationBack) {
  DAGCircuit dag;
  dag.add_qubits(1);
  EXPECT_EQ(dag.get_multi_graph().num_nodes(), 2);
  dag.apply_operation_back(make_gate("x", {0}));
  EXPECT_EQ(dag.get_multi_graph().num_nodes(), 3);
}

TEST(DAGCircuitTest, ApplyOperationFront) {
  DAGCircuit dag;
  dag.add_qubits(1);
  dag.apply_operation_front(make_gate("x", {0}));
  EXPECT_EQ(dag.get_multi_graph().num_nodes(), 3);
}

TEST(DAGCircuitTest, SizeDepthWidth) {
  DAGCircuit dag;
  dag.add_qubits(3);
  EXPECT_EQ(dag.size(), 0);
  EXPECT_EQ(dag.depth(), 0);
  EXPECT_EQ(dag.width(), 3);

  dag.apply_operation_back(make_gate("x", {0}));
  dag.apply_operation_back(make_gate("h", {1}));
  EXPECT_EQ(dag.size(), 2);
  EXPECT_EQ(dag.depth(), 1);

  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_front(make_gate("h", {0}));
  EXPECT_EQ(dag.size(), 4);
  EXPECT_EQ(dag.depth(), 3);
}

TEST(DAGCircuitTest, TopologicalNodes) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("h", {1}));

  auto nodes = dag.topological_nodes();
  auto op_nodes = dag.topological_op_nodes();

  ASSERT_EQ(nodes.size(), 7u);
  ASSERT_EQ(op_nodes.size(), 3u);
  EXPECT_EQ(op_nodes[0]->name(), "h");
  EXPECT_EQ(op_nodes[1]->name(), "cx");
  EXPECT_EQ(op_nodes[2]->name(), "h");
}

TEST(DAGCircuitTest, TwoAndMultiQubitOps) {
  DAGCircuit dag;
  dag.add_qubits(3);
  dag.apply_operation_back(make_gate("x", {0}));
  dag.apply_operation_back(make_gate("h", {1}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("ccx", {0, 1, 2}));
  EXPECT_EQ(dag.two_qubit_ops().size(), 1u);
  EXPECT_EQ(dag.multi_qubit_ops().size(), 1u);
}

TEST(DAGCircuitTest, LongestPath) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("h", {1}));

  auto path = dag.longest_path();
  ASSERT_EQ(path.size(), 5u);
  EXPECT_NE(dynamic_cast<DAGInNode*>(path[0]), nullptr);
  EXPECT_EQ(dynamic_cast<DAGOpNode*>(path[1])->name(), "h");
  EXPECT_EQ(dynamic_cast<DAGOpNode*>(path[2])->name(), "cx");
  EXPECT_EQ(dynamic_cast<DAGOpNode*>(path[3])->name(), "h");
  EXPECT_NE(dynamic_cast<DAGOutNode*>(path[4]), nullptr);
}

TEST(DAGCircuitTest, SuccessorsAndPredecessors) {
  DAGCircuit dag;
  dag.add_qubits(2);
  auto node1 = dag.apply_operation_back(make_gate("h", {0}));
  auto node2 = dag.apply_operation_back(make_gate("h", {1}));
  auto node3 = dag.apply_operation_back(make_gate("cx", {0, 1}));
  auto node4 = dag.apply_operation_back(make_gate("h", {0}));
  auto node5 = dag.apply_operation_back(make_gate("h", {1}));

  auto node1_successors = dag.successors(node1);
  auto node1_predecessors = dag.predecessors(node1);
  EXPECT_EQ(node1_successors.size(), 1u);
  EXPECT_EQ(dynamic_cast<DAGOpNode*>(node1_successors[0])->name(), "cx");
  EXPECT_EQ(node1_predecessors.size(), 1u);
  EXPECT_NE(dynamic_cast<DAGInNode*>(node1_predecessors[0]), nullptr);

  auto node3_successors = dag.successors(node3);
  auto node3_predecessors = dag.predecessors(node3);
  EXPECT_EQ(node3_successors.size(), 2u);
  EXPECT_EQ(node3_predecessors.size(), 2u);
  EXPECT_FALSE(dag.is_successor(node2, node1));
  EXPECT_TRUE(dag.is_successor(node2, node3));
  EXPECT_TRUE(dag.is_predecessor(node4, node3));
  EXPECT_TRUE(dag.is_predecessor(node5, node3));
}

TEST(DAGCircuitTest, RemoveOpNode) {
  DAGCircuit dag;
  dag.add_qubits(2);
  auto node1 = dag.apply_operation_back(make_gate("h", {0}));
  auto node2 = dag.apply_operation_back(make_gate("cx", {0, 1}));
  EXPECT_EQ(dag.node_counter(), 6);
  dag.remove_op_node(node1);
  EXPECT_EQ(dag.node_counter(), 5);
  dag.remove_op_node(node2);
  EXPECT_EQ(dag.node_counter(), 4);
}

TEST(DAGCircuitTest, CountOpsAndNodesOnWire) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_front(make_gate("h", {0}));
  dag.apply_operation_front(make_gate("h", {1}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));

  auto counts = dag.count_ops();
  EXPECT_EQ(counts["h"], 2);
  EXPECT_EQ(counts["cx"], 1);

  auto wire0_nodes = dag.nodes_on_wire(0, true);
  EXPECT_EQ(wire0_nodes.size(), 2u);
  EXPECT_NE(dynamic_cast<DAGOpNode*>(wire0_nodes[0]), nullptr);
}

TEST(DAGCircuitTest, IrToDagCircuitToDagAndBack) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      make_gate("h", {0}), make_gate("cx", {0, 1}), make_gate("h", {1})};

  auto dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(dag.op_nodes().size(), 3u);

  QuantumCircuit circuit(2);
  circuit.append(make_gate("h", {0}));
  circuit.append(make_gate("cx", {0, 1}));
  circuit.append(make_gate("h", {1}));
  auto dag_from_circuit = DAGCircuit::circuit_to_dag(circuit);
  EXPECT_EQ(dag_from_circuit.op_nodes().size(), 3u);

  auto roundtrip = dag.dag_to_circuit();
  EXPECT_EQ(roundtrip->num_qubits(), 2);
  EXPECT_EQ(roundtrip->get_operations().size(), 3u);
}

TEST(DAGCircuitTest, TwoQubitOpsToDagAndEdges) {
  DAGCircuit dag;
  dag.add_qubits(3);
  dag.apply_operation_front(make_gate("h", {0}));
  dag.apply_operation_front(make_gate("h", {1}));
  dag.apply_operation_front(make_gate("h", {2}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("cx", {1, 2}));

  auto new_dag = dag.two_qubit_ops_to_dag();
  EXPECT_EQ(new_dag.get_input_map().size(), 3u);
  EXPECT_EQ(new_dag.get_output_map().size(), 3u);
  EXPECT_EQ(new_dag.get_multi_graph().num_nodes(), 8);

  int op_to_op_edges = 0;
  for (const auto& edge : dag.edges()) {
    if (dynamic_cast<DAGOpNode*>(edge.src) &&
        dynamic_cast<DAGOpNode*>(edge.dst)) {
      ++op_to_op_edges;
    }
  }
  EXPECT_EQ(op_to_op_edges, 4);
}

TEST(DAGCircuitTest, ParameterizeAndDeparameterizeRz) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("s", {0}));
  dag.apply_operation_back(make_gate("tdg", {1}));
  dag.parameterize_all_rz();

  auto ops = dag.topological_op_nodes();
  ASSERT_EQ(ops.size(), 2u);
  EXPECT_EQ(ops[0]->name(), "rz");
  EXPECT_EQ(ops[1]->name(), "rz");

  dag.deparameterize_all_rz();
  ops = dag.topological_op_nodes();
  EXPECT_EQ(ops[0]->name(), "s");
  EXPECT_EQ(ops[1]->name(), "tdg");
}

TEST(DAGCircuitTest, DeparameterizeIdentityRemovesNode) {
  DAGCircuit dag;
  dag.add_qubits(1);
  dag.apply_operation_back(make_gate("rz", {0}, {0.0}));
  EXPECT_EQ(dag.size(), 1);
  dag.deparameterize_all_rz();
  EXPECT_EQ(dag.size(), 0);
}

TEST(DAGCircuitTest, CollectRunsAndAncestry) {
  DAGCircuit dag;
  dag.add_qubits(2);
  auto h0 = dag.apply_operation_back(make_gate("h", {0}));
  auto h1 = dag.apply_operation_back(make_gate("h", {0}));
  auto cx = dag.apply_operation_back(make_gate("cx", {0, 1}));

  auto runs = dag.collect_runs({"h"});
  EXPECT_EQ(runs.size(), 1u);

  auto ancestors = dag.ancestors(cx);
  auto descendants = dag.descendants(h0);
  EXPECT_EQ(ancestors.size(), 4u);
  EXPECT_GE(descendants.size(), 2u);
  EXPECT_TRUE(dag.is_successor(h1, cx));
}

TEST(DAGCircuitTest, CollectRunsTwoAdjacentCx) {
  DAGCircuit dag;
  dag.add_qubits(3);
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("cx", {1, 2}));

  EXPECT_EQ(normalize_run_signatures(dag.collect_runs({"cx"})),
            (std::vector<std::vector<std::string>>{{"cx[0,1]"}, {"cx[1,2]"}}));
}

TEST(DAGCircuitTest, CollectRunsWideThreeWireBlock) {
  DAGCircuit dag;
  dag.add_qubits(3);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("cx", {1, 2}));
  dag.apply_operation_back(make_gate("h", {2}));

  EXPECT_EQ(normalize_run_signatures(dag.collect_runs({"h", "cx"})),
            (std::vector<std::vector<std::string>>{
                {"cx[1,2]"}, {"h[2]"}, {"h[0]", "cx[0,1]"}}));
}

TEST(DAGCircuitTest, CollectRunsWideThreeWireBranch) {
  DAGCircuit dag;
  dag.add_qubits(3);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("cx", {1, 2}));
  dag.apply_operation_back(make_gate("h", {1}));
  dag.apply_operation_back(make_gate("h", {2}));

  EXPECT_EQ(normalize_run_signatures(dag.collect_runs({"h", "cx"})),
            (std::vector<std::vector<std::string>>{
                {"cx[1,2]"}, {"h[1]"}, {"h[2]"}, {"h[0]", "cx[0,1]"}}));
}

TEST(DAGCircuitTest, CollectRunsWideFourWireBlock) {
  DAGCircuit dag;
  dag.add_qubits(4);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("cx", {1, 2}));
  dag.apply_operation_back(make_gate("cx", {2, 3}));
  dag.apply_operation_back(make_gate("h", {3}));

  EXPECT_EQ(normalize_run_signatures(dag.collect_runs({"h", "cx"})),
            (std::vector<std::vector<std::string>>{
                {"cx[1,2]"}, {"cx[2,3]"}, {"h[3]"}, {"h[0]", "cx[0,1]"}}));
}

TEST(DAGCircuitTest, CollectRunsOnlyExtendsForward) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("h", {1}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));

  EXPECT_EQ(
      normalize_run_signatures(dag.collect_runs({"h", "cx"})),
      (std::vector<std::vector<std::string>>{{"h[0]"}, {"h[1]", "cx[0,1]"}}));
}

TEST(DAGCircuitTest, ConstructorStartsEmpty) {
  DAGCircuit dag;
  const DAGCircuit& const_dag = dag;

  EXPECT_TRUE(dag.wires().empty());
  EXPECT_EQ(dag.node_counter(), 0);
  EXPECT_EQ(dag.size(), 0);
  EXPECT_EQ(dag.depth(), 0);
  EXPECT_EQ(dag.width(), 0);
  EXPECT_TRUE(dag.nodes().empty());
  EXPECT_TRUE(dag.op_nodes().empty());
  EXPECT_TRUE(dag.longest_path().empty());
  EXPECT_TRUE(dag.get_input_map().empty());
  EXPECT_TRUE(dag.get_output_map().empty());
  EXPECT_EQ(const_dag.get_multi_graph().num_nodes(), 0);
}

TEST(DAGCircuitTest, AddQubitsZeroIsNoOp) {
  DAGCircuit dag;

  dag.add_qubits(0);

  EXPECT_TRUE(dag.wires().empty());
  EXPECT_EQ(dag.node_counter(), 0);
  EXPECT_EQ(dag.width(), 0);
}

TEST(DAGCircuitTest, AddQubitsDuplicateThrowsWithoutPartialMutation) {
  DAGCircuit dag;
  dag.add_qubits(2);

  EXPECT_THROW(dag.add_qubits(1), std::invalid_argument);
  EXPECT_EQ(dag.wires(), (std::vector<int>{0, 1}));
  EXPECT_EQ(dag.node_counter(), 4);
  EXPECT_EQ(dag.get_input_map().size(), 2u);
  EXPECT_EQ(dag.get_output_map().size(), 2u);
}

TEST(DAGCircuitTest, ApplyOperationBackUsesTargetsAndUpdatesCounts) {
  DAGCircuit dag;
  dag.add_qubits(2);

  auto x = dag.apply_operation_back(make_gate("x", {0}));
  auto cx = dag.apply_operation_back(make_gate("cx", {0, 1}));

  ASSERT_NE(x, nullptr);
  ASSERT_NE(cx, nullptr);
  EXPECT_EQ(op_names(dag.topological_op_nodes()),
            (std::vector<std::string>{"x", "cx"}));
  EXPECT_EQ(node_ids(dag.nodes_on_wire(0, true)),
            (std::vector<int>{x->node_id(), cx->node_id()}));
  EXPECT_EQ(dag.count_ops().at("x"), 1);
  EXPECT_EQ(dag.count_ops().at("cx"), 1);
}

TEST(DAGCircuitTest, ApplyOperationFrontPrependsOperations) {
  DAGCircuit dag;
  dag.add_qubits(1);

  auto x = dag.apply_operation_back(make_gate("x", {0}));
  auto h = dag.apply_operation_front(make_gate("h", {0}));

  ASSERT_NE(x, nullptr);
  ASSERT_NE(h, nullptr);
  EXPECT_EQ(op_names(dag.topological_op_nodes()),
            (std::vector<std::string>{"h", "x"}));
  EXPECT_TRUE(dag.is_successor(h, x));
  EXPECT_TRUE(dag.is_predecessor(x, h));
}

TEST(DAGCircuitTest, NodesOnWireReturnsAllNodesAndOnlyOps) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_front(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));

  EXPECT_EQ(node_labels(dag.nodes_on_wire(0, false)),
            (std::vector<std::string>{"in", "h", "cx", "out"}));
  EXPECT_EQ(node_labels(dag.nodes_on_wire(0, true)),
            (std::vector<std::string>{"h", "cx"}));
  EXPECT_EQ(node_labels(dag.nodes_on_wire(1, false)),
            (std::vector<std::string>{"in", "cx", "out"}));
}

TEST(DAGCircuitTest, NodesOnWireRejectsUnknownWire) {
  DAGCircuit dag;
  dag.add_qubits(1);

  EXPECT_THROW(dag.nodes_on_wire(3), std::invalid_argument);
}

TEST(DAGCircuitTest, TopologicalOpNodesRespectCustomKey) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("x", {0}));
  dag.apply_operation_back(make_gate("h", {1}));

  auto custom = dag.topological_op_nodes([](const DAGNode* current) {
    if (auto* op = dynamic_cast<const DAGOpNode*>(current)) {
      return op->name() == "x" ? std::string("z") : std::string("a");
    }
    return current->sort_key();
  });

  EXPECT_EQ(op_names(dag.topological_op_nodes()),
            (std::vector<std::string>{"x", "h"}));
  EXPECT_EQ(op_names(custom), (std::vector<std::string>{"h", "x"}));
}

TEST(DAGCircuitTest, NodeNodesAndOpNodesReflectActiveGraphState) {
  DAGCircuit dag;
  dag.add_qubits(2);
  auto h = dag.apply_operation_back(make_gate("h", {0}));
  auto cx = dag.apply_operation_back(make_gate("cx", {0, 1}));

  EXPECT_EQ(dag.node(h->node_id()), h);
  EXPECT_EQ(dag.nodes().size(), 6u);
  EXPECT_EQ(dag.op_nodes().size(), 2u);

  dag.remove_op_node(h);

  EXPECT_EQ(dag.node(h->node_id()), nullptr);
  EXPECT_EQ(dag.nodes().size(), 5u);
  ASSERT_EQ(dag.op_nodes().size(), 1u);
  EXPECT_EQ(dag.op_nodes()[0], cx);
}

TEST(DAGCircuitTest, LongestPathFindsFiveQubitCriticalChain) {
  auto dag = build_five_qubit_chain();

  EXPECT_EQ(node_labels(dag.longest_path()),
            (std::vector<std::string>{"in", "h", "cx", "cx", "cx", "cx", "h",
                                      "out"}));
  EXPECT_EQ(dag.depth(), 6);
}

TEST(DAGCircuitTest, AncestorsAndDescendantsTraverseTransitively) {
  auto dag = build_five_qubit_chain();
  auto ops = dag.topological_op_nodes();
  auto first = ops.front();
  auto last = ops.back();

  auto ancestors = dag.ancestors(last);
  auto descendants = dag.descendants(first);

  EXPECT_TRUE(
      contains_node_id(ancestors, dag.get_input_map().at(0)->node_id()));
  EXPECT_TRUE(
      contains_node_id(ancestors, dag.get_input_map().at(4)->node_id()));
  EXPECT_TRUE(contains_node_id(ancestors, ops[1]->node_id()));
  EXPECT_FALSE(
      contains_node_id(ancestors, dag.get_output_map().at(4)->node_id()));
  EXPECT_TRUE(contains_node_id(descendants, ops[1]->node_id()));
  EXPECT_TRUE(contains_node_id(descendants, last->node_id()));
  EXPECT_TRUE(
      contains_node_id(descendants, dag.get_output_map().at(0)->node_id()));
}

TEST(DAGCircuitTest, RemoveOpNodeRetainsConnectivityAndClearsNodeSlot) {
  DAGCircuit dag;
  dag.add_qubits(1);
  auto h = dag.apply_operation_back(make_gate("h", {0}));
  auto x = dag.apply_operation_back(make_gate("x", {0}));
  auto z = dag.apply_operation_back(make_gate("z", {0}));

  dag.remove_op_node(x);

  EXPECT_TRUE(dag.is_successor(h, z));
  EXPECT_EQ(dag.count_ops().count("x"), 0u);
  EXPECT_EQ(dag.node(x->node_id()), nullptr);
  EXPECT_EQ(x->flag, -1);
  EXPECT_EQ(dag.size(), 2);
}

TEST(DAGCircuitTest, RemoveOpNodeRejectsNullptr) {
  DAGCircuit dag;

  EXPECT_THROW(dag.remove_op_node(nullptr), std::invalid_argument);
}

TEST(DAGCircuitTest, RenameOpAcceptsPhaseConversionsAndUpdatesCounts) {
  DAGCircuit dag;
  dag.add_qubits(1);
  auto node = dag.apply_operation_back(make_gate("rz", {0}, {kPi / 2.0}));
  auto s = make_gate("s", {0});

  dag.rename_op(node->op, s);
  node->op = s;
  EXPECT_EQ(dag.count_ops().count("rz"), 0u);
  EXPECT_EQ(dag.count_ops().at("s"), 1);

  auto rz = make_gate("rz", {0}, {kPi / 2.0});
  dag.rename_op(node->op, rz);
  node->op = rz;
  EXPECT_EQ(dag.count_ops().count("s"), 0u);
  EXPECT_EQ(dag.count_ops().at("rz"), 1);
}

TEST(DAGCircuitTest, RenameOpRejectsInvalidConversionOrMissingOp) {
  DAGCircuit dag;
  dag.add_qubits(1);
  auto node = dag.apply_operation_back(make_gate("x", {0}));

  EXPECT_THROW(dag.rename_op(node->op, make_gate("h", {0})),
               std::invalid_argument);
  EXPECT_THROW(
      dag.rename_op(make_gate("rz", {0}, {kPi / 4.0}), make_gate("t", {0})),
      std::invalid_argument);
}

TEST(DAGCircuitTest, ParameterizeAllRzConvertsEveryPhaseGateOnFiveQubits) {
  DAGCircuit dag;
  dag.add_qubits(5);
  dag.apply_operation_back(make_gate("s", {0}));
  dag.apply_operation_back(make_gate("t", {1}));
  dag.apply_operation_back(make_gate("sdg", {2}));
  dag.apply_operation_back(make_gate("tdg", {3}));
  dag.apply_operation_back(make_gate("z", {4}));

  dag.parameterize_all_rz();

  auto ops = dag.topological_op_nodes();
  ASSERT_EQ(ops.size(), 5u);
  EXPECT_EQ(op_names(ops),
            (std::vector<std::string>{"rz", "rz", "rz", "rz", "rz"}));
  EXPECT_NEAR(ops[0]->op->arg_value[0], kPi / 2.0, 1e-12);
  EXPECT_NEAR(ops[1]->op->arg_value[0], kPi / 4.0, 1e-12);
  EXPECT_NEAR(ops[2]->op->arg_value[0], -kPi / 2.0, 1e-12);
  EXPECT_NEAR(ops[3]->op->arg_value[0], -kPi / 4.0, 1e-12);
  EXPECT_NEAR(ops[4]->op->arg_value[0], kPi, 1e-12);
}

TEST(DAGCircuitTest, ParameterizeAllRzSkipsNonPhaseGates) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("x", {0}));
  dag.apply_operation_back(make_gate("h", {1}));

  dag.parameterize_all_rz();

  EXPECT_EQ(op_names(dag.topological_op_nodes()),
            (std::vector<std::string>{"x", "h"}));
  EXPECT_EQ(dag.count_ops().at("x"), 1);
  EXPECT_EQ(dag.count_ops().at("h"), 1);
}

TEST(DAGCircuitTest, DeparameterizeAllRzConvertsIdentityAndQuarterTurns) {
  DAGCircuit dag;
  dag.add_qubits(5);
  dag.apply_operation_back(make_gate("rz", {0}, {0.0}));
  dag.apply_operation_back(make_gate("rz", {1}, {kPi / 4.0}));
  dag.apply_operation_back(make_gate("rz", {2}, {kPi / 2.0}));
  dag.apply_operation_back(make_gate("rz", {3}, {kPi}));
  dag.apply_operation_back(make_gate("rz", {4}, {-kPi / 4.0}));

  dag.deparameterize_all_rz();

  EXPECT_EQ(op_names(dag.topological_op_nodes()),
            (std::vector<std::string>{"t", "s", "z", "tdg"}));
  EXPECT_EQ(dag.size(), 4);
  EXPECT_EQ(node_labels(dag.nodes_on_wire(0, false)),
            (std::vector<std::string>{"in", "out"}));
}

TEST(DAGCircuitTest, DeparameterizeAllRzHonorsTolerance) {
  DAGCircuit loose;
  loose.add_qubits(1);
  loose.apply_operation_back(make_gate("rz", {0}, {kPi / 4.0 + 5e-9}));
  loose.deparameterize_all_rz(1e-8);
  EXPECT_EQ(op_names(loose.topological_op_nodes()),
            (std::vector<std::string>{"t"}));

  DAGCircuit strict;
  strict.add_qubits(1);
  strict.apply_operation_back(make_gate("rz", {0}, {kPi / 4.0 + 5e-9}));
  strict.deparameterize_all_rz(1e-10);
  EXPECT_EQ(op_names(strict.topological_op_nodes()),
            (std::vector<std::string>{"rz"}));
}

TEST(DAGCircuitTest, CountOpsTracksRenamesAndRemovals) {
  DAGCircuit dag;
  dag.add_qubits(2);
  auto s = dag.apply_operation_back(make_gate("s", {0}));
  auto cx = dag.apply_operation_back(make_gate("cx", {0, 1}));

  dag.parameterize_all_rz();
  dag.remove_op_node(cx);

  auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("s"), 0u);
  EXPECT_EQ(counts.at("rz"), 1);
  EXPECT_EQ(counts.count("cx"), 0u);
  EXPECT_EQ(dag.topological_op_nodes()[0], s);
}

TEST(DAGCircuitTest, IrToDagHandlesEmptyInput) {
  auto dag = DAGCircuit::ir_to_dag({});

  EXPECT_TRUE(dag.wires().empty());
  EXPECT_EQ(dag.size(), 0);
  EXPECT_EQ(dag.depth(), 0);
}

TEST(DAGCircuitTest, CircuitToDagPreservesExplicitCircuitWidth) {
  QuantumCircuit circuit(5);
  circuit.append(make_gate("h", {0}));
  circuit.append(make_gate("cx", {0, 1}));

  auto dag = DAGCircuit::circuit_to_dag(circuit);

  EXPECT_EQ(dag.width(), 5);
  EXPECT_EQ(dag.wires(), (std::vector<int>{0, 1, 2, 3, 4}));
  EXPECT_EQ(op_names(dag.topological_op_nodes()),
            (std::vector<std::string>{"h", "cx"}));
}

TEST(DAGCircuitTest, DagToCircuitPreservesIdleQubitsByDefault) {
  DAGCircuit dag;
  dag.add_qubits(5);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));

  auto circuit = dag.dag_to_circuit();

  EXPECT_EQ(circuit->num_qubits(), 5);
  EXPECT_EQ(circuit->get_operations().size(), 2u);
}

TEST(DAGCircuitTest, DagToCircuitHonorsExplicitWidth) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("h", {0}));

  auto circuit = dag.dag_to_circuit(7);

  EXPECT_EQ(circuit->num_qubits(), 7);
  EXPECT_EQ(circuit->get_operations().size(), 1u);
}

TEST(DAGCircuitTest, TwoQubitOpsToDagFiltersAndCopies) {
  DAGCircuit dag;
  dag.add_qubits(5);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("cx", {0, 1}));
  dag.apply_operation_back(make_gate("ccx", {1, 2, 3}));
  dag.apply_operation_back(make_gate("cx", {3, 4}));

  auto filtered = dag.two_qubit_ops_to_dag();

  EXPECT_EQ(filtered.width(), 5);
  EXPECT_EQ(op_names(filtered.topological_op_nodes()),
            (std::vector<std::string>{"cx", "cx"}));
  dag.apply_operation_back(make_gate("cx", {1, 2}));
  EXPECT_EQ(filtered.size(), 2);
}

TEST(DAGCircuitTest, EdgesReturnAllEdgesAndSubsetEdges) {
  DAGCircuit dag;
  dag.add_qubits(2);
  dag.apply_operation_back(make_gate("h", {0}));
  dag.apply_operation_back(make_gate("h", {1}));
  auto cx = dag.apply_operation_back(make_gate("cx", {0, 1}));

  EXPECT_EQ(normalize_edge_signatures(dag.edges()),
            (std::vector<std::tuple<std::string, std::string, int>>{
                {"cx[0,1]", "out[0]", 0},
                {"cx[0,1]", "out[1]", 1},
                {"h[0]", "cx[0,1]", 0},
                {"h[1]", "cx[0,1]", 1},
                {"in[0]", "h[0]", 0},
                {"in[1]", "h[1]", 1},
            }));

  std::vector<DAGNode*> subset = {cx};
  EXPECT_EQ(normalize_edge_signatures(dag.edges(&subset)),
            (std::vector<std::tuple<std::string, std::string, int>>{
                {"cx[0,1]", "out[0]", 0},
                {"cx[0,1]", "out[1]", 1},
            }));
}

TEST(DAGCircuitTest, CollectRunsWideFiveQubitBlock) {
  auto dag = build_five_qubit_chain();

  EXPECT_EQ(normalize_run_signatures(dag.collect_runs({"h", "cx"})),
            (std::vector<std::vector<std::string>>{{"cx[1,2]"},
                                                   {"cx[2,3]"},
                                                   {"cx[3,4]"},
                                                   {"h[4]"},
                                                   {"h[0]", "cx[0,1]"}}));
}
