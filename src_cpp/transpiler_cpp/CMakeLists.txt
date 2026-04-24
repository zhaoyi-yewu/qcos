cmake_minimum_required(VERSION 3.16)
project(transpiler LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)  # 禁用编译器扩展，使用标准 C++

if (MSVC)
    add_compile_definitions(_USE_MATH_DEFINES)
    add_compile_options(/utf-8)
endif()

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wno-attributes)
endif()

include_directories(${PROJECT_SOURCE_DIR}/include
                    ${PROJECT_SOURCE_DIR}/third_party
                    ${PROJECT_SOURCE_DIR}/third_party/googletest
                    ${PROJECT_SOURCE_DIR}/third_party/googletest/include
                    ${PROJECT_SOURCE_DIR}/third_party/pybind11/include
                    ${PROJECT_SOURCE_DIR}/third_party/antlr4/runtime/src)

set(LIB_TRANSPILER ${PROJECT_NAME})
set(LIB_GTEST gtest)
set(LIB_ANTLR4 antlr4)

option(USE_PYQCOS "use transpiler in python" ON)
option(USE_STUBGEN "generate pyi files" ON)

add_subdirectory(third_party)
add_subdirectory(src)
add_subdirectory(tests)
if(USE_PYQCOS)
    add_subdirectory(qcos_bindings)
endif(USE_PYQCOS)
message(STATUS "USE_PYQCOS=" ${USE_PYQCOS})