cmake_minimum_required(VERSION 3.16)
project(high_performance)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB_RECURSE LIB_PYQCOS_SRC_CPP
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)
set(LIB_PYQCOS ${PROJECT_NAME})

set(LIBRARY_OUTPUT_PATH ${PROJECT_BINARY_DIR}/lib)
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/bin)

pybind11_add_module(${LIB_PYQCOS} ${LIB_PYQCOS_SRC_CPP})
set_target_properties(${LIB_PYQCOS}  PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${EXECUTABLE_OUTPUT_PATH})
# TODO: 将qcos替换为变量值
target_link_libraries(${LIB_PYQCOS} PRIVATE qcos)

# .so文件输出路径
set(PYQCOS_OUT_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../dist")
# 自动识别扩展后缀
set(PYQCOS_OUT_LIB
    "$<TARGET_FILE_NAME:${LIB_PYQCOS}>"
)

# 拷贝.so到目标目录
add_custom_command(TARGET ${LIB_PYQCOS}
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory ${PYQCOS_OUT_PATH}
    COMMAND ${CMAKE_COMMAND} -E copy
            $<TARGET_FILE:${LIB_PYQCOS}>
            ${PYQCOS_OUT_PATH}
)

# 自动生成pyi文件（使用pip安装的pybind11-stubgen）
if(USE_STUBGEN)
  add_custom_command(TARGET ${LIB_PYQCOS}
      POST_BUILD
      COMMAND python3
              -m pybind11_stubgen
              ${LIB_PYQCOS}
              -o ${PYQCOS_OUT_PATH}
      WORKING_DIRECTORY ${EXECUTABLE_OUTPUT_PATH}
      VERBATIM
      USES_TERMINAL
  )
endif(USE_STUBGEN)
