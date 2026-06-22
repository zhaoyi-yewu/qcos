# QCOS 变更日志

本文件记录该项目所有显著变更。

## [未发布] - 开发中

### 新增功能

- 支持用户管理功能：项目/用户/角色增删改查、登录、权限管理等
- 新增下发校准命令、获取校准结果、设置设备选项、获取设备选项等北向接口
- 初步支持监控功能：暴露设备状态监控、作业状态监控等监控数据，可对接Prometheus等监控系统
- 支持QCOS独立数据库，主要存储用户信息、作业信息，数据库后端可对接PostgreSQL、sqlite等关系型数据库
- get-jobs接口支持过滤project_id, user_id, job_id列表
- 新增汉原脉冲驱动
- 初步支持QEC Shor码(基于Stim仿真器)
- 支持量子编译器性能脚本测试
- 支持量子电路等价性判断
- 支持高性能解析器选项
- 支持QUBO任务拆分选项：可支持提交大QUBO任务，可提供QUBO拆分能力
- 支持量子电路转化为任意真机的基础门集

### 变更功能

- 改进Config配置模块，增加{SECTION}，从Config.{VALUE}改为Config.{SECTION}.Value形式，这样可以支持不同SECTION的同名参数
- 取消作业触发后，不再等待30秒，而是在调用driver_cancel成功后立即返回，不等待清理

### 修复问题

- 无

### 移除内容

- 无

## [1.1.0] - 2026-03-20

### 新增功能

- 新增可配置的环境变量PREFECT_WORKER_QUERY_SECONDS、PREFECT_WORKER_PREFETCH_SECONDS，加速worker检查新作业的速度
- 支持自动编译python3环境，可用来兼容部分老旧的CPU
- 隔离部分驱动依赖库，默认位置: /var/lib/qcos/venv；通过install-venvs.py脚本自动安装各驱动的venv环境
- 工作流中默认加载驱动的venv环境
- 部分编译和检查脚本使用venv环境
- 支持以TXT或者JSON文档形式保存量子任务结果
- 新增设备的device-monitor进程用来实时同步设备信息，并支持独立的日志

### 变更功能

- 改进deployment的创建方式，启动qcos时直接根据设备名创建，而不是作业执行时创建
- requirements目录中的各驱动相关requirements-DRIVER.txt挪到requirements/drivers目录下
- 启动驱动的prefect worker从线程改为进程
- prefect worker查询作业时间(PREFECT_WORKER_QUERY_SECONDS)从15秒改为1秒，大幅降低提交作业后等待的时间
- 修改部分驱动的默认转译器
- 移除job-engine.log, 改为在各驱动配置文件独立配置

### 修复问题

- 无

### 移除内容

- 无

## [1.0.1] - 2026-01-19

### 新增功能

- 升级prefect镜像到3.6.9版本
- 增加bumpversion版本号更新脚本: cicd/release-version.py
- 增加版本发布脚本: cicd/publish.py
- 增加部分文档: 贡献者公约、代码贡献指南等等
- 新增qutip模拟器驱动

### 变更功能

- 由于PYPI包名冲突，修改模块包名qcos->wy_qcos，qcos.client->wy_qcos_client，并挪到src目录
- 量子任务的执行方式由串行执行更改为并行执行
- requirements\*.txt文件统一放入requirements目录
- 更换html文档主题从alabaster改为sphinx_rtd_theme
- 修改量旋核磁驱动，使用cmss转译器

### 修复问题

- 修复在没有配置PIP_MIRROR时的wheel包编译报错问题

### 移除内容

- 无

## [1.0.0] - 2025-12-17

### 新增功能

- 支持 JSON-RPC API 接口
- 支持作业全生命周期管理：提交、查询、删除、取消
- 支持修改排队中作业的优先级
- 作业提交时支持选择转译器，可选类型：
  - 五岳转译器（cmss）
  - Qiskit 转译器（qiskit）
- 五岳转译器（cmss）支持功能：QASM 解析、逻辑门分解、量子比特映射、编译优化
- 作业提交时支持选择后端驱动，可选类型：测试驱动、中科酷原中性原子驱动、玻色光量子伊辛机驱动等
- 支持多设备并行操作能力
- 支持设备独立配置文件管理及查询功能
- 支持获取作业运行各阶段性能评估数据（Profiling）
- 支持单元测试（UT）和系统测试（ST）
- 提供命令行工具（qcos-cli）
- 支持容器化部署，配套一键编译/运行脚本
- 支持配置全局最大作业数限制、最大排队+运行作业数限制
- 支持日志轮转配置：可设置最大日志文件大小、日志文件保留数量

### 变更功能

- 无

### 修复问题

- 无

### 移除内容

- 无
