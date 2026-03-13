cmake_minimum_required(VERSION 3.16)

add_library(${PROJECT_NAME} STATIC circuit/base_operation.cpp)

target_include_directories(${PROJECT_NAME} PUBLIC
    ${PROJECT_SOURCE_DIR}/include
)