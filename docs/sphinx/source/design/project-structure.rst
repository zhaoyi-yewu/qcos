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
   * - .agents
     - AI辅助编程规范和技能，包括：
        - rules: AI agent规则(core/code/ask)，约束沟通语言、编码规范等
        - skills: 技能定义，包括新功能模块和新设备驱动的分步开发流程
        - integrations: 各类AI编码工具的集成说明
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
        - 角色权限casbin规则配置文件: etc/qcos/roles/\*.conf
        - ST配置文件: etc/qcos/qcos-st.toml
        - ST设备独立配置文件: etc/qcos/st-conf.d/\*.toml
        - openssl证书配置文件: etc/ssl/openssl.conf
   * - requirements
     - 创建QCOS以及设备驱动运行的Python虚拟环境(venv)的相关模板和脚本
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
   * - src/wy_qcos/db
     - 数据库模块，包括：
        - models: ORM表模型定义(作业、设备、用户、项目、Flavor、设备组、可用率等)
        - repositories: 数据仓储层，封装各资源的增删改查
        - migration: alembic数据库表结构迁移脚本
        - utils: 数据库工具，包括作业存储后端抽象(SQL/Redis)和常用数据操作
   * - src/wy_qcos/device
     - 设备实现，包括：
        - Device: 设备实例，绑定设备与驱动，维护设备状态/工作状态
        - DeviceManager: 从配置文件加载设备并管理设备生命周期
        - DeviceGroupManager: 设备分组管理
   * - src/wy_qcos/drivers
     - 驱动实现。包括：厂商驱动、模拟器驱动、测试驱动等
   * - src/wy_qcos/engine
     - 量子工作引擎，包括：量子QASM/QUBO代码解析、转译、驱动调用、回调、聚合、性能评估等等
   * - src/wy_qcos/flavor
     - Flavor预设调度策略管理，包括FlavorManager、DeviceGroupManager
   * - src/wy_qcos/log
     - 日志配置模块
   * - src/wy_qcos/metrics
     - 系统监控模块，包括：
        - 系统健康指标
        - 作业/API指标统计
        - 设备可用率采集与聚合（DeviceAvailabilityCollector/Scheduler/Task）
   * - src/wy_qcos/qec
     - 量子纠错(QEC)，包括：
        - QuantumCodeBase: 量子纠错码抽象基类(编码、错误注入、
          综合征测量、纠错、解码)
        - ShorCode: Shor码实现
        - QecFactory: 纠错码工厂，按名称创建纠错码实例
   * - src/wy_qcos/qem
     - 量子错误缓解(QEM)，包括：
        - ZNEMitigation: 零噪声外推缓解
        - ReadoutMitigation: 读出误差缓解(REM)
        - DDMitigation: 动力学解耦缓解(DD)
        - MitigationFactory/MitigationManager: 缓解器工厂与缓解流水线编排
          (线路变换、变体生成、结果校正与外推)
   * - src/wy_qcos/scheduler
     - 自动调度器模块，包括：Filter（过滤器）、Weigher（权重器）、DeviceState、RequestSpec、AutoScheduler
   * - src/wy_qcos/task_manager
     - 任务管理和调度
   * - src/wy_qcos/tests
     - 单元测试、系统测试和性能测试用例
   * - src/wy_qcos/transpiler
     - 量子转译器插件实现
   * - src/wy_qcos/user
     - 用户管理和权限管理
   * - src/wy_qcos_client
     - QCOS命令行和客户端实现
   * - src_cpp/transpiler_cpp
     - C++实现的转译器模块，提供Python接口
   * - webui
     - Web前端界面（Vue.js）
