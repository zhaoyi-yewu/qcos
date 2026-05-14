cmake_minimum_required(VERSION 3.16)

add_library(${LIB_TRANSPILER} STATIC
                            circuit/base_operation.cpp
                            circuit/dag_circuit.cpp
                            circuit/dag_node.cpp
                            circuit/multi_graph.cpp
                            circuit/gate_operation.cpp
                            circuit/quantum_circuit.cpp
                            decomposer/equivalence_graph.cpp
                            decomposer/rule_applier.cpp
                            decomposer/decomposer.cpp
                            mapping/greedy_routing.cpp
                            mapping/sabre_routing.cpp
                            mapping/mcts_routing.cpp
                            mapping/sabre_mapping.cpp
                            utils/load_files.cpp
                            compiler/operations/classic_controlled_operation.cpp
                            compiler/operations/compound_operation.cpp
                            compiler/operations/expression.cpp
                            compiler/operations/non_unitary_operation.cpp
                            compiler/operations/operation.cpp
                            compiler/operations/standard_operation.cpp
                            compiler/operations/symbolic_operation.cpp
                            compiler/qasm_compiler/parser/passes/const_eval_pass.cpp
                            compiler/qasm_compiler/parser/passes/type_check_pass.cpp
                            compiler/qasm_compiler/parser/parser.cpp
                            compiler/qasm_compiler/parser/scanner.cpp
                            compiler/qasm_compiler/parser/statement.cpp
                            compiler/qasm_compiler/parser/types.cpp
                            compiler/qasm_compiler/qasm_lexer.cpp
                            compiler/qasm_compiler/qasm_parser.cpp
                            compiler/qasm_to_origin_ir.cpp
                            compiler/quantum_computation.cpp
                            )


target_include_directories(${LIB_TRANSPILER} PUBLIC
    ${PROJECT_SOURCE_DIR}/include
)

target_compile_definitions(${LIB_TRANSPILER} PUBLIC $<$<CONFIG:Debug>:LOG_DEBUG>)
target_compile_definitions(${LIB_TRANSPILER} PUBLIC $<$<CONFIG:Release>:TEST_BENCH>)
