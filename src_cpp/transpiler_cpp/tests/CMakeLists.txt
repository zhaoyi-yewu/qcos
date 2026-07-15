cmake_minimum_required(VERSION 3.11)

include_directories(${PROJECT_SOURCE_DIR}/include)

set(TEST_NAME ${PROJECT_NAME}_test)

add_executable(${TEST_NAME} test_main.cpp
                            test_base_operations.cpp
                            test_adjacent_optimization.cpp
                            test_dag_circuit.cpp
                            test_multi_graph.cpp
                            test_gate_operations.cpp
                            test_inverse_cancellation.cpp
                            test_quantum_circuit.cpp
                            test_subcircuit_rewrite.cpp
                            test_template.cpp
                            test_clifford_rz_optimization.cpp
                            decomposer/test_decomposer.cpp
                            decomposer/test_decomposer_benchmark.cpp
                            test_sabre_routing.cpp
                            test_sabre_mapping.cpp
                            test_chip_data.cpp
                            test_qasm_to_ir.cpp
                            test_parallel_optimize.cpp
                            test_qasm_converter.cpp
                            test_qpu_verifier.cpp
)
target_link_libraries(${TEST_NAME} ${LIB_TRANSPILER} ${LIB_GTEST} ${LIB_ANTLR4})

target_compile_definitions(${TEST_NAME} PRIVATE
    TEST_DATA_DIR="${PROJECT_SOURCE_DIR}/../../samples/"
    TEST_TOPOLOGY_DIR="${PROJECT_SOURCE_DIR}/../../etc/"
)
