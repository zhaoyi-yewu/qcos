cmake_minimum_required(VERSION 3.11)
project(high_performance)

set(LIB_HIGH_PERF ${PROJECT_NAME})

file(GLOB_RECURSE LIB_BINDING_SRC_CPP ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp)

set(PROJECT_OUT_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../dist")

nanobind_add_module(${LIB_HIGH_PERF} ${LIB_BINDING_SRC_CPP})

target_compile_features(${LIB_HIGH_PERF} PRIVATE cxx_std_17)

set_target_properties(${LIB_HIGH_PERF} PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${PROJECT_OUT_PATH})

target_link_libraries(${LIB_HIGH_PERF} PRIVATE ${LIB_TRANSPILER} ${LIB_ANTLR4})

if(USE_STUBGEN)
    add_custom_command(TARGET ${LIB_HIGH_PERF}
        POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E env
                PYTHONPATH=${PROJECT_OUT_PATH}
                python3 -m nanobind_stubgen ${LIB_HIGH_PERF} --out ${PROJECT_OUT_PATH}
        VERBATIM
        USES_TERMINAL
    )
endif(USE_STUBGEN)
