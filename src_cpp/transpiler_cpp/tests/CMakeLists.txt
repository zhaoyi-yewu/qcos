cmake_minimum_required(VERSION 3.16)

include_directories(${PROJECT_SOURCE_DIR}/include)

set(TEST_NAME ${PROJECT_NAME}_test)
add_executable(${TEST_NAME} test_main.cpp test_operations.cpp)
target_link_libraries(${TEST_NAME} ${PROJECT_NAME} ${LIB_GTEST})