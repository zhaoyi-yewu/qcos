项目代码目录结构
===================

代码目录和功能如下:

.. list-table:: 项目代码目录结构
   :widths: 20 80
   :header-rows: 1
   :align: left
   :class: longtable

   * - 目录/文件路径
     - 功能说明
   * - bin
     - 二进制工具，包括：独立的转译器工具、加解密工具、证书制作工具等等
   * - build-scripts
     - 编译工具，包括：容器、wheel包、文档等的构建和运行脚本
   * - deploy-scripts
     - 部署工具，包括：
        - 部署到K8s的yaml模板和脚本
   * - cicd
     - CICD持续化集成相关工具，包括：
        - 代码格式和安全检查工具
        - 单元测试(UT)
        - 代码覆盖率测试(Coverage)
        - 系统集成测试(ST)
        - 容器镜像推送脚本
        - 社区代码同步脚本
        - 版本发布脚本
   * - docs
     - 文档源代码、API文档模板，及相关文档生成工具
   * - etc
     - 系统配置文件示例：
        - 全局配置文件: etc/qcos/qcos.toml
        - 设备独立配置文件: etc/qcos/conf.d/\*.toml
        - ST配置文件: etc/qcos/qcos-st.toml
        - openssl证书配置文件: etc/ssl/openssl.conf
   * - samples
     - qasm2.0、qasm3.0、qubo等输入示例文件
   * - src/wy_qcos/api
     - 北向API接口定义和实现
   * - src/wy_qcos/api/posiq
     - 北向JSON-RPC接口，主要是fast-api框架相关的资源定义
   * - src/wy_qcos/api/schemas
     - 北向接口中各资源和参数的数据模板、数据结构定义
   * - src/wy_qcos/common
     - 公共定义。包括：配置、常量定义、错误码定义、通用库等
   * - src/wy_qcos/drivers
     - 驱动实现。包括：厂商驱动、模拟器驱动、测试驱动等
   * - src/wy_qcos/engine
     - 量子工作引擎，包括：量子QASM/QUBO代码解析、转译、驱动调用、回调、聚合、性能评估等等
   * - src/wy_qcos/log
     - 日志配置模块
   * - src/wy_qcos/task_manager
     - 任务管理和调度
   * - src/wy_qcos/tests
     - 单元测试、系统测试和性能测试用例
   * - src/wy_qcos/transpiler
     - 量子转译器插件实现
   * - src/wy_qcos/user
     - 用户管理和权限管理
   * - src/wy_qcos/libs
     - 第三方库
   * - src/wy_qcos_client
     - QCOS命令行和客户端实现
