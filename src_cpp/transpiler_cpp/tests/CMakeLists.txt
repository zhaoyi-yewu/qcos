cmake_minimum_required(VERSION 3.16)

include_directories(${PROJECT_SOURCE_DIR}/include)

set(TEST_NAME ${PROJECT_NAME}_test)

add_executable(${TEST_NAME} test_main.cpp
                            test_base_operations.cpp
                            test_gate_operations.cpp
                            test_sabre_routing.cpp
)
target_link_libraries(${TEST_NAME} ${PROJECT_NAME} ${LIB_GTEST})

target_compile_definitions(${TEST_NAME} PRIVATE 
    TEST_DATA_DIR="${PROJECT_SOURCE_DIR}/../../samples/"
    TEST_TOPOLOGY_DIR="${PROJECT_SOURCE_DIR}/../../etc/"
)
