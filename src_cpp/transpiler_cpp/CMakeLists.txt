cmake_minimum_required(VERSION 3.11)
project(transpiler LANGUAGES CXX)

find_package(Threads REQUIRED)

# 根据平台和实际路径存在性添加 cmake 搜索路径，避免硬编码
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    # RHEL/CentOS/openEuler/MOS 等 lib64 体系
    if(EXISTS "/usr/lib64/cmake")
        list(APPEND CMAKE_PREFIX_PATH /usr/lib64/cmake)
    endif()
    if(EXISTS "/usr/local/lib64/cmake")
        list(APPEND CMAKE_PREFIX_PATH /usr/local/lib64/cmake)
    endif()
    # Debian/Ubuntu multiarch 体系
    if(EXISTS "/usr/lib/x86_64-linux-gnu/cmake")
        list(APPEND CMAKE_PREFIX_PATH /usr/lib/x86_64-linux-gnu/cmake)
    endif()
    if(EXISTS "/usr/local/lib/x86_64-linux-gnu/cmake")
        list(APPEND CMAKE_PREFIX_PATH /usr/local/lib/x86_64-linux-gnu/cmake)
    endif()
elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    # macOS
    if(EXISTS "/usr/local/lib/cmake")
        list(APPEND CMAKE_PREFIX_PATH /usr/local/lib/cmake)
    endif()
    if(EXISTS "/opt/homebrew/lib/cmake")
        list(APPEND CMAKE_PREFIX_PATH /opt/homebrew/lib/cmake)
    endif()
endif()

# ---- GTest ----
find_package(GTest CONFIG QUIET)
if(GTest_FOUND)
    message(STATUS "Found pre-installed GTest via CONFIG")
    set(LIB_GTEST GTest::gtest GTest::gtest_main)
else()
    find_package(GTest QUIET)
    if(GTest_FOUND AND GTEST_LIBRARIES AND GTEST_INCLUDE_DIRS)
        message(STATUS "Found pre-installed GTest via FindModule: ${GTEST_LIBRARIES}")
        include_directories(${GTEST_INCLUDE_DIRS})
        set(LIB_GTEST ${GTEST_LIBRARIES})
    else()
        set(LIB_GTEST "")
    endif()
endif()

option(USE_PYQCOS "use transpiler in python" ON)
option(USE_STUBGEN "generate pyi files" OFF)

# ---- Boost (header-only: Boost.Graph for VF2 layout) ----
find_package(Boost QUIET)
if(Boost_FOUND)
    include_directories(${Boost_INCLUDE_DIRS})
    message(STATUS "Found Boost via find_package: ${Boost_INCLUDE_DIRS}")
else()
    find_path(BOOST_INCLUDE_DIR boost/graph/vf2_sub_graph_iso.hpp
        PATHS /usr/local/include /usr/include /opt/homebrew/include)
    if(NOT BOOST_INCLUDE_DIR)
        message(FATAL_ERROR
            "Boost headers not found.")
    endif()
    include_directories(${BOOST_INCLUDE_DIR})
    message(STATUS "Found Boost headers at: ${BOOST_INCLUDE_DIR}")
endif()

if(USE_PYQCOS)
    find_package(Python 3.11 REQUIRED COMPONENTS Interpreter Development.Module
                 OPTIONAL_COMPONENTS Development.SABIModule)
    execute_process(
        COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
        OUTPUT_VARIABLE nanobind_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
endif()

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
                    ${PROJECT_SOURCE_DIR}/third_party/antlr4/runtime/src
                    ${Python_INCLUDE_DIRS})

set(LIB_TRANSPILER ${PROJECT_NAME})
set(LIB_ANTLR4 antlr4)

add_subdirectory(third_party)
add_subdirectory(src)
add_subdirectory(tests)
if(USE_PYQCOS)
    add_subdirectory(qcos_bindings)
endif(USE_PYQCOS)
message(STATUS "USE_PYQCOS=" ${USE_PYQCOS})
