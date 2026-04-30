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
#include <memory>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#include "circuit/dag_node.h"
#include "circuit/gate_operation.h"
#include "circuit/multi_graph.h"

using namespace qcos;

namespace {

struct WireEndpoints {
  int input_id;
  int output_id;
};

std::shared_ptr<DAGOpNode> make_op_node(const std::string& name,
                                        const std::vector<int>& qargs,
                                        int flag = 0) {
  auto node = std::make_shared<DAGOpNode>(
      std::shared_ptr<BaseOperation>(create_gate(name, qargs)), qargs);
  node->flag = flag;
  return node;
}

WireEndpoints add_wire(MultiGraph& graph, int wire) {
  auto input = std::make_shared<DAGInNode>(wire);
  auto output = std::make_shared<DAGOutNode>(wire);
  auto [input_id, output_id] = graph.add_nodes(input, output);
  graph.add_edge(input_id, output_id, wire);
  return {input_id, output_id};
}

std::vector<int> node_ids(const std::vector<std::shared_ptr<DAGNode>>& nodes) {
  std::vector<int> ids;
  ids.reserve(nodes.size());
  for (const auto& node : nodes) {
    ids.push_back(node->node_id());
  }
  return ids;
}

bool has_weighted_edge(const MultiGraph& graph, int src, int dst, int wire) {
  for (const auto& [edge_src, edge_dst, edge_wire] : graph.out_edges(src)) {
    if (edge_src == src && edge_dst == dst && edge_wire == wire) {
      return true;
    }
  }
  return false;
}

std::vector<int> topo_ids(const std::vector<std::shared_ptr<DAGNode>>& nodes) {
  return node_ids(nodes);
}

std::vector<std::vector<int>> normalize_run_ids(
    const std::vector<std::vector<std::shared_ptr<DAGNode>>>& runs) {
  std::vector<std::vector<int>> normalized;
  normalized.reserve(runs.size());
  for (const auto& run : runs) {
    normalized.push_back(node_ids(run));
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

size_t run_width(const std::vector<std::shared_ptr<DAGNode>>& run) {
  std::vector<int> wires;
  for (const auto& node : run) {
    auto op = std::dynamic_pointer_cast<DAGOpNode>(node);
    if (!op) {
      continue;
    }
    wires.insert(wires.end(), op->qargs.begin(), op->qargs.end());
  }
  std::sort(wires.begin(), wires.end());
  wires.erase(std::unique(wires.begin(), wires.end()), wires.end());
  return wires.size();
}

}  // namespace

TEST(MultiGraphTest, AddAndAccess) {
  MultiGraph graph;
  auto [in_id, out_id] = graph.add_nodes(std::make_shared<DAGInNode>(0),
                                         std::make_shared<DAGOutNode>(0));
  const int h_id = graph.add_node(make_op_node("h", {0}, 11));

  EXPECT_EQ(in_id, 0);
  EXPECT_EQ(out_id, 1);
  EXPECT_EQ(h_id, 2);
  EXPECT_EQ(graph.num_nodes(), 3);
  EXPECT_EQ(graph[h_id]->node_id(), h_id);

  auto replacement = make_op_node("x", {0}, 12);
  replacement->set_node_id(h_id);
  graph[h_id] = replacement;

  const MultiGraph& const_graph = graph;
  auto replaced = std::dynamic_pointer_cast<DAGOpNode>(const_graph[h_id]);
  ASSERT_NE(replaced, nullptr);
  EXPECT_EQ(replaced->name(), "x");
  EXPECT_EQ(replaced->flag, 12);
}

TEST(MultiGraphTest, HasEdgeAndNodes) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  int h1_id = graph.add_node(make_op_node("h", {0}, 1));
  int h2_id = graph.add_node(make_op_node("h", {0}, 2));
  graph.add_edge(wire0.input_id, h1_id, 0);
  graph.add_edge(h1_id, h2_id, 0);
  graph.add_edge(h2_id, wire0.output_id, 0);

  EXPECT_TRUE(graph.has_edge(h1_id, h2_id));
  EXPECT_FALSE(graph.has_edge(-1, h2_id));
  EXPECT_FALSE(graph.has_edge(h1_id, 99));

  graph.remove_node_retain_edges(h1_id);

  EXPECT_FALSE(graph.has_edge(h1_id, h2_id));
  EXPECT_EQ(graph.num_nodes(), 3);
  auto active_nodes = node_ids(graph.nodes());
  std::sort(active_nodes.begin(), active_nodes.end());
  EXPECT_EQ(active_nodes,
            (std::vector<int>{wire0.input_id, wire0.output_id, h2_id}));
}

TEST(MultiGraphTest, NeighborQueries) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  auto wire1 = add_wire(graph, 1);
  int cx_id = graph.add_node(make_op_node("cx", {0, 1}, 3));
  graph.insert_node_on_in_edges_multiple(cx_id,
                                         {wire0.output_id, wire1.output_id});

  EXPECT_EQ(node_ids(graph.successors(wire0.input_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.successors(wire1.input_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.predecessors(wire0.output_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.predecessors(wire1.output_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(graph.successor_indices(wire0.input_id), std::vector<int>{cx_id});
  EXPECT_EQ(graph.predecessor_indices(wire1.output_id),
            std::vector<int>{cx_id});

  auto cx_edges = graph.out_edges(cx_id);
  ASSERT_EQ(cx_edges.size(), 2u);
  EXPECT_TRUE(has_weighted_edge(graph, cx_id, wire0.output_id, 0));
  EXPECT_TRUE(has_weighted_edge(graph, cx_id, wire1.output_id, 1));
}

TEST(MultiGraphTest, FindByEdge) {
  MultiGraph graph;
  int pred0 = graph.add_node(make_op_node("h", {0}, 10));
  int pred1 = graph.add_node(make_op_node("x", {1}, 11));
  int center = graph.add_node(make_op_node("cx", {0, 1}, 12));
  int succ0 = graph.add_node(make_op_node("h", {2}, 13));
  int succ1 = graph.add_node(make_op_node("x", {3}, 14));
  int succ2 = graph.add_node(make_op_node("z", {4}, 15));
  graph.add_edge(pred0, center, 7);
  graph.add_edge(pred1, center, 7);
  graph.add_edge(center, succ0, 7);
  graph.add_edge(center, succ1, 7);
  graph.add_edge(center, succ2, 9);

  auto first = graph.find_first_successor_by_edge(
      center, [](int wire) { return wire == 7; });
  ASSERT_NE(first, nullptr);
  EXPECT_EQ(first->node_id(), succ0);
  EXPECT_EQ(graph.find_first_successor_by_edge(
                center, [](int wire) { return wire == 99; }),
            nullptr);

  auto pred_matches = node_ids(graph.find_predecessors_by_edge(
      center, [](int wire) { return wire == 7; }));
  auto succ_matches = node_ids(graph.find_successors_by_edge(
      center, [](int wire) { return wire == 7; }));
  std::sort(pred_matches.begin(), pred_matches.end());
  std::sort(succ_matches.begin(), succ_matches.end());
  EXPECT_EQ(pred_matches, (std::vector<int>{pred0, pred1}));
  EXPECT_EQ(succ_matches, (std::vector<int>{succ0, succ1}));
}

TEST(MultiGraphTest, InsertInSingle) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);

  const int h_id = graph.add_node(make_op_node("h", {0}, 20));
  graph.insert_node_on_in_edges_multiple(h_id, {wire0.output_id});

  auto preds = graph.predecessors(wire0.output_id);
  auto succs = graph.successors(wire0.input_id);
  ASSERT_EQ(preds.size(), 1u);
  ASSERT_EQ(succs.size(), 1u);
  EXPECT_EQ(preds[0]->node_id(), h_id);
  EXPECT_EQ(succs[0]->node_id(), h_id);
  EXPECT_FALSE(graph.has_edge(wire0.input_id, wire0.output_id));
}

TEST(MultiGraphTest, InsertInMultiple) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  auto wire1 = add_wire(graph, 1);
  const int cx_id = graph.add_node(make_op_node("cx", {0, 1}, 21));
  graph.insert_node_on_in_edges_multiple(cx_id,
                                         {wire0.output_id, wire1.output_id});

  EXPECT_EQ(node_ids(graph.successors(wire0.input_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.successors(wire1.input_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.predecessors(wire0.output_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.predecessors(wire1.output_id)),
            std::vector<int>{cx_id});
}

TEST(MultiGraphTest, InsertOutSingle) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);

  const int h_id = graph.add_node(make_op_node("h", {0}, 22));
  graph.insert_node_on_out_edges_multiple(h_id, {wire0.input_id});

  EXPECT_EQ(node_ids(graph.successors(wire0.input_id)),
            std::vector<int>{h_id});
  EXPECT_EQ(node_ids(graph.predecessors(wire0.output_id)),
            std::vector<int>{h_id});
  EXPECT_FALSE(graph.has_edge(wire0.input_id, wire0.output_id));
}

TEST(MultiGraphTest, InsertOutMultiple) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  auto wire1 = add_wire(graph, 1);

  const int cx_id = graph.add_node(make_op_node("cx", {0, 1}, 23));
  graph.insert_node_on_out_edges_multiple(cx_id,
                                          {wire0.input_id, wire1.input_id});

  EXPECT_EQ(node_ids(graph.successors(wire0.input_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.successors(wire1.input_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.predecessors(wire0.output_id)),
            std::vector<int>{cx_id});
  EXPECT_EQ(node_ids(graph.predecessors(wire1.output_id)),
            std::vector<int>{cx_id});
}

TEST(MultiGraphTest, RemoveRetainMatchWire) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  int h1_id = graph.add_node(make_op_node("h", {0}, 30));
  int h2_id = graph.add_node(make_op_node("h", {0}, 31));
  graph.add_edge(wire0.input_id, h1_id, 0);
  graph.add_edge(h1_id, h2_id, 0);
  graph.add_edge(h2_id, wire0.output_id, 0);

  EXPECT_EQ(graph.dag_longest_path_length(), 3);
  graph.remove_node_retain_edges(h1_id);
  EXPECT_TRUE(graph.has_edge(wire0.input_id, h2_id));
  EXPECT_FALSE(graph.has_edge(h1_id, h2_id));
  EXPECT_EQ(graph.num_nodes(), 3);
  EXPECT_EQ(graph.dag_longest_path_length(), 2);
}

TEST(MultiGraphTest, RemoveRetainNoCrossWire) {
  MultiGraph graph;
  int pred0 = graph.add_node(make_op_node("h", {0}, 32));
  int pred1 = graph.add_node(make_op_node("x", {1}, 33));
  int center_id = graph.add_node(make_op_node("cx", {0, 1}, 34));
  int succ0 = graph.add_node(make_op_node("z", {0}, 35));
  int succ1 = graph.add_node(make_op_node("h", {1}, 36));
  graph.add_edge(pred0, center_id, 0);
  graph.add_edge(pred1, center_id, 1);
  graph.add_edge(center_id, succ0, 0);
  graph.add_edge(center_id, succ1, 1);

  graph.remove_node_retain_edges(center_id);

  EXPECT_TRUE(graph.has_edge(pred0, succ0));
  EXPECT_TRUE(graph.has_edge(pred1, succ1));
  EXPECT_FALSE(graph.has_edge(pred0, succ1));
  EXPECT_FALSE(graph.has_edge(pred1, succ0));
  EXPECT_EQ(node_ids(graph.predecessors(succ0)), std::vector<int>{pred0});
  EXPECT_EQ(node_ids(graph.predecessors(succ1)), std::vector<int>{pred1});
}

TEST(MultiGraphTest, LexTopoByKey) {
  MultiGraph graph;
  int x_id = graph.add_node(make_op_node("x", {0}, 80));
  int h_id = graph.add_node(make_op_node("h", {0}, 81));
  int h2_id = graph.add_node(make_op_node("h", {1}, 82));
  graph.add_edge(x_id, h2_id, 0);

  auto order = topo_ids(graph.lexicographical_topological_sort(
      [](const std::shared_ptr<DAGNode>& node) {
        if (auto op = std::dynamic_pointer_cast<DAGOpNode>(node)) {
          return op->name();
        }
        return std::string();
      }));

  EXPECT_EQ(order, (std::vector<int>{h_id, x_id, h2_id}));
}

TEST(MultiGraphTest, LexTopoSkipsInactive) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  int h_id = graph.add_node(make_op_node("h", {0}, 83));
  graph.insert_node_on_in_edges_multiple(h_id, {wire0.output_id});
  graph.remove_node_retain_edges(h_id);

  auto order = topo_ids(graph.lexicographical_topological_sort(
      [](const std::shared_ptr<DAGNode>& node) { return node->sort_key(); }));
  std::sort(order.begin(), order.end());
  EXPECT_EQ(order, (std::vector<int>{wire0.input_id, wire0.output_id}));
}

TEST(MultiGraphTest, LongestPathEmpty) {
  MultiGraph graph;
  EXPECT_EQ(graph.dag_longest_path_length(), 0);
  EXPECT_TRUE(graph.dag_longest_path().empty());
}

TEST(MultiGraphTest, LongestPathChain) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  int h1 = graph.add_node(make_op_node("h", {0}, 90));
  int h2 = graph.add_node(make_op_node("x", {0}, 91));
  int short_branch = graph.add_node(make_op_node("z", {0}, 92));
  graph.add_edge(wire0.input_id, h1, 0);
  graph.add_edge(h1, h2, 0);
  graph.add_edge(h2, wire0.output_id, 0);
  graph.add_edge(wire0.input_id, short_branch, 0);

  EXPECT_EQ(graph.dag_longest_path_length(), 3);
  EXPECT_EQ(graph.dag_longest_path(),
            (std::vector<int>{wire0.input_id, h1, h2, wire0.output_id}));
}

TEST(MultiGraphTest, CollectRunsChain) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  int h1 = graph.add_node(make_op_node("h", {0}, 100));
  int h2 = graph.add_node(make_op_node("h", {0}, 101));
  int x1 = graph.add_node(make_op_node("x", {0}, 102));
  int h3 = graph.add_node(make_op_node("h", {0}, 103));
  graph.add_edge(wire0.input_id, h1, 0);
  graph.add_edge(h1, h2, 0);
  graph.add_edge(h2, x1, 0);
  graph.add_edge(x1, h3, 0);
  graph.add_edge(h3, wire0.output_id, 0);

  auto runs = graph.collect_runs([](const std::shared_ptr<DAGNode>& node) {
    auto op = std::dynamic_pointer_cast<DAGOpNode>(node);
    return op && op->name() == "h";
  });

  ASSERT_EQ(runs.size(), 2u);
  EXPECT_EQ(node_ids(runs[0]), (std::vector<int>{h1, h2}));
  EXPECT_EQ(node_ids(runs[1]), (std::vector<int>{h3}));
}

TEST(MultiGraphTest, CollectRunsTwoQubitBlock) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  auto wire1 = add_wire(graph, 1);
  int cx1 = graph.add_node(make_op_node("cx", {0, 1}, 104));
  graph.insert_node_on_in_edges_multiple(cx1,
                                         {wire0.output_id, wire1.output_id});
  int cx2 = graph.add_node(make_op_node("cx", {0, 1}, 105));
  graph.insert_node_on_in_edges_multiple(cx2,
                                         {wire0.output_id, wire1.output_id});
  int h0 = graph.add_node(make_op_node("h", {0}, 106));
  graph.insert_node_on_in_edges_multiple(h0, {wire0.output_id});

  auto runs = graph.collect_runs([](const std::shared_ptr<DAGNode>& node) {
    auto op = std::dynamic_pointer_cast<DAGOpNode>(node);
    return op && op->name() == "cx";
  });

  ASSERT_EQ(runs.size(), 1u);
  EXPECT_EQ(node_ids(runs[0]), (std::vector<int>{cx1, cx2}));
}

TEST(MultiGraphTest, CollectRunsWideThreeWireBlock) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  auto wire1 = add_wire(graph, 1);
  auto wire2 = add_wire(graph, 2);
  int h0 = graph.add_node(make_op_node("h", {0}, 107));
  graph.insert_node_on_in_edges_multiple(h0, {wire0.output_id});
  int cx01 = graph.add_node(make_op_node("cx", {0, 1}, 108));
  graph.insert_node_on_in_edges_multiple(cx01,
                                         {wire0.output_id, wire1.output_id});
  int cx12 = graph.add_node(make_op_node("cx", {1, 2}, 109));
  graph.insert_node_on_in_edges_multiple(cx12,
                                         {wire1.output_id, wire2.output_id});
  int h2 = graph.add_node(make_op_node("h", {2}, 110));
  graph.insert_node_on_in_edges_multiple(h2, {wire2.output_id});

  auto runs = graph.collect_runs([](const std::shared_ptr<DAGNode>& node) {
    auto op = std::dynamic_pointer_cast<DAGOpNode>(node);
    return op && (op->name() == "h" || op->name() == "cx");
  });

  ASSERT_EQ(runs.size(), 3u);
  EXPECT_EQ(node_ids(runs[0]), (std::vector<int>{h0, cx01}));
  EXPECT_EQ(node_ids(runs[1]), (std::vector<int>{cx12}));
  EXPECT_EQ(node_ids(runs[2]), (std::vector<int>{h2}));
  EXPECT_EQ(run_width(runs[0]), 2u);
}

TEST(MultiGraphTest, CollectRunsWideThreeWireBranch) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  auto wire1 = add_wire(graph, 1);
  auto wire2 = add_wire(graph, 2);
  int h0 = graph.add_node(make_op_node("h", {0}, 111));
  graph.insert_node_on_in_edges_multiple(h0, {wire0.output_id});
  int cx01 = graph.add_node(make_op_node("cx", {0, 1}, 112));
  graph.insert_node_on_in_edges_multiple(cx01,
                                         {wire0.output_id, wire1.output_id});
  int cx12 = graph.add_node(make_op_node("cx", {1, 2}, 113));
  graph.insert_node_on_in_edges_multiple(cx12,
                                         {wire1.output_id, wire2.output_id});
  int h1 = graph.add_node(make_op_node("h", {1}, 114));
  graph.insert_node_on_in_edges_multiple(h1, {wire1.output_id});
  int h2 = graph.add_node(make_op_node("h", {2}, 115));
  graph.insert_node_on_in_edges_multiple(h2, {wire2.output_id});

  auto runs = graph.collect_runs([](const std::shared_ptr<DAGNode>& node) {
    auto op = std::dynamic_pointer_cast<DAGOpNode>(node);
    return op && (op->name() == "h" || op->name() == "cx");
  });

  auto normalized = normalize_run_ids(runs);
  ASSERT_EQ(normalized.size(), 4u);
  EXPECT_EQ(normalized,
            (std::vector<std::vector<int>>{{cx12}, {h1}, {h2}, {h0, cx01}}));
}

TEST(MultiGraphTest, CollectRunsWideFourWireBlock) {
  MultiGraph graph;
  auto wire0 = add_wire(graph, 0);
  auto wire1 = add_wire(graph, 1);
  auto wire2 = add_wire(graph, 2);
  auto wire3 = add_wire(graph, 3);
  int h0 = graph.add_node(make_op_node("h", {0}, 116));
  graph.insert_node_on_in_edges_multiple(h0, {wire0.output_id});
  int cx01 = graph.add_node(make_op_node("cx", {0, 1}, 117));
  graph.insert_node_on_in_edges_multiple(cx01,
                                         {wire0.output_id, wire1.output_id});
  int cx12 = graph.add_node(make_op_node("cx", {1, 2}, 118));
  graph.insert_node_on_in_edges_multiple(cx12,
                                         {wire1.output_id, wire2.output_id});
  int cx23 = graph.add_node(make_op_node("cx", {2, 3}, 119));
  graph.insert_node_on_in_edges_multiple(cx23,
                                         {wire2.output_id, wire3.output_id});
  int h3 = graph.add_node(make_op_node("h", {3}, 120));
  graph.insert_node_on_in_edges_multiple(h3, {wire3.output_id});

  auto runs = graph.collect_runs([](const std::shared_ptr<DAGNode>& node) {
    auto op = std::dynamic_pointer_cast<DAGOpNode>(node);
    return op && (op->name() == "h" || op->name() == "cx");
  });

  ASSERT_EQ(runs.size(), 4u);
  EXPECT_EQ(node_ids(runs[0]), (std::vector<int>{h0, cx01}));
  EXPECT_EQ(node_ids(runs[1]), (std::vector<int>{cx12}));
  EXPECT_EQ(node_ids(runs[2]), (std::vector<int>{cx23}));
  EXPECT_EQ(node_ids(runs[3]), (std::vector<int>{h3}));
  EXPECT_EQ(run_width(runs[0]), 2u);
}

TEST(MultiGraphTest, CollectRunsSplitAtBranch) {
  MultiGraph graph;
  int h1 = graph.add_node(make_op_node("h", {0}, 110));
  int h2 = graph.add_node(make_op_node("h", {1}, 111));
  int h3 = graph.add_node(make_op_node("h", {2}, 112));
  graph.add_edge(h1, h2, 0);
  graph.add_edge(h1, h3, 1);

  auto runs = graph.collect_runs([](const std::shared_ptr<DAGNode>& node) {
    auto op = std::dynamic_pointer_cast<DAGOpNode>(node);
    return op && op->name() == "h";
  });

  EXPECT_EQ(normalize_run_ids(runs),
            (std::vector<std::vector<int>>{{h1}, {h2}, {h3}}));
}