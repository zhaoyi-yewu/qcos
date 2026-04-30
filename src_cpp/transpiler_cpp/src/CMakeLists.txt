cmake_minimum_required(VERSION 3.16)

add_library(${LIB_TRANSPILER} SHARED
                            circuit/base_operation.cpp
                            circuit/dag_node.cpp
                            circuit/multi_graph.cpp
                            circuit/gate_operation.cpp
                            circuit/quantum_circuit.cpp
                            mapping/greedy_routing.cpp
                            mapping/sabre_routing.cpp
                            mapping/mcts_routing.cpp
                            mapping/sabre_mapping.cpp
                            utils/load_files.cpp
                            )


target_include_directories(${LIB_TRANSPILER} PUBLIC
    ${PROJECT_SOURCE_DIR}/include
)

target_compile_definitions(${LIB_TRANSPILER} PUBLIC $<$<CONFIG:Debug>:LOG_DEBUG>)
target_compile_definitions(${LIB_TRANSPILER} PUBLIC $<$<CONFIG:Release>:TEST_BENCH>)
