cmake_minimum_required(VERSION 3.16)
project(qcos LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)  # 禁用编译器扩展，使用标准 C++

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

include_directories(${PROJECT_SOURCE_DIR}/include
                    ${PROJECT_SOURCE_DIR}/third_party
                    ${PROJECT_SOURCE_DIR}/third_party/googletest
                    ${PROJECT_SOURCE_DIR}/third_party/googletest/include)

set(LIB_GTEST gtest)

add_subdirectory(third_party)
add_subdirectory(src)
add_subdirectory(tests)
