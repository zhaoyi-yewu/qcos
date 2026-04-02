cmake_minimum_required(VERSION 3.16)

add_library(${LIB_TRANSPILER} SHARED
                            circuit/base_operation.cpp
                            circuit/gate_operation.cpp
                            mapping/sabre_routing.cpp
                            utils/load_files.cpp
                            mapping/mcts_routing.cpp
                            )


target_include_directories(${LIB_TRANSPILER} PUBLIC
    ${PROJECT_SOURCE_DIR}/include
)

target_compile_definitions(${LIB_TRANSPILER} PUBLIC $<$<CONFIG:Debug>:LOG_DEBUG>)
target_compile_definitions(${LIB_TRANSPILER} PUBLIC $<$<CONFIG:Release>:TEST_BENCH>)
