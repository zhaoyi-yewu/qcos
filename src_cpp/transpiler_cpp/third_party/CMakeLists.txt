cmake_minimum_required(VERSION 3.11)

# ---- GTest ----
if(NOT GTest_FOUND AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/googletest/CMakeLists.txt)
    message(STATUS "GTest not found, building from local source")
    add_subdirectory(googletest)
    include_directories(${CMAKE_CURRENT_SOURCE_DIR}/googletest
                        ${CMAKE_CURRENT_SOURCE_DIR}/googletest/include)
    set(LIB_GTEST gtest PARENT_SCOPE)
elseif(NOT GTest_FOUND)
    message(FATAL_ERROR
        "GTest not found! Either install it on the system:\n"
        "  yum install gtest-devel\n"
        "Or provide local source at: ${CMAKE_CURRENT_SOURCE_DIR}/googletest/\n"
    )
endif()

if(USE_PYQCOS)
    find_package(nanobind CONFIG REQUIRED)
endif()
add_subdirectory(antlr4)
