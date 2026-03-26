cmake_minimum_required(VERSION 3.16)

add_library(${PROJECT_NAME} SHARED
                            circuit/base_operation.cpp
                            circuit/gate_operation.cpp
                            mapping/sabre_routing.cpp
                            utils/load_files.cpp)

target_include_directories(${PROJECT_NAME} PUBLIC
    ${PROJECT_SOURCE_DIR}/include
)

target_compile_definitions(${PROJECT_NAME} PUBLIC $<$<CONFIG:Debug>:LOG_DEBUG>)
target_compile_definitions(${PROJECT_NAME} PUBLIC $<$<CONFIG:Release>:TEST_BENCH>)
