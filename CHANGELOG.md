# QCOS 变更日志

本文件记录该项目所有显著变更。

## [未发布] - 开发中

### 新增功能

- 新增Flavor（预设资源调度策略）管理功能：支持通过API和CLI创建、查询、删除Flavor
- 新增Device Group（设备分组）功能：支持设备逻辑分组管理，包含增删改查API和CLI命令
- 新增DeviceGroupFilter调度过滤器，根据device group成员列表过滤候选设备
- 支持量子作业自动调度功能：用户提交作业时不指定backend，由系统自动选择后端设备
- 新增自动调度器，支持10个Filter和3个Weigher
- Job表新增flavor_id和extra_specs字段
- submit-job命令新增--flavor-id和--extra-specs参数，--backend改为可选
- 新增show-mem命令：查询API服务端进程内存占用（RSS/VMS/线程数/GC对象数/CPU使用率）
- 新增gc命令：手动触发Python垃圾回收，支持指定回收代数（0/1/2）
- 新增trace-mem命令：通过tracemalloc追踪内存分配，返回当前/峰值内存及Top内存分配统计
- 新增设置设备维护模式功能：支持通过API和CLI将设备设为维护模式
- 新增设备可用率（availability）统计功能：通过Redis订阅采集设备运行状态，
  内存计数器实时累计，整点聚合落库到device_availability_hourly表
- 新增DeviceAvailabilityCollector单例：后台线程psubscribe设备运行信息频道，
  按设备累计online_count/total_count，支持snapshot_and_reset与get_rate
- 新增DeviceAvailabilityScheduler：APScheduler CronTrigger整点触发
  aggregate_availability_hourly任务
- 新增DeviceAvailabilityWeigher：基于设备可用率加权，可用率越高权重越大
- 新增extra_specs服务器端白名单校验：submit-job的extra_specs字典key
  必须为支持的调度字段，否则返回bad_request
- 新增Flavor extra_properties统一消费：qcos:devices（白名单）、
  qcos:exclude_devices（黑名单）、qcos:code_types（覆盖job code_type）、
  qc:tech_types（技术类型过滤）、qc:device_availability（可用率阈值）
- 新增DeviceNameFilter：合并白名单和黑名单逻辑，qcos:devices的"all"表示不限制
- 新增DeviceAvailabilityFilter：基于qc:device_availability阈值过滤设备
- get_device接口响应新增metrics字段：availability_hourly、availability_total、
  avg_1q_fidelity、avg_2q_fidelity，均保留5位小数
- list-devices命令输出新增availability_total列
- get_avg_1q_fidelity/get_avg_2q_fidelity从calibration.qubit_metrics
  /coupler_metrics提取xeb_fidelity/cz_fidelity，无数据返回None
- 新增InputConstraintsFilter调度过滤器：校验作业的shots、
  circuit_aggregation、driver_options、transpiler_options是否满足
  驱动声明的约束schema（input_constrains、driver_options_schema、
  transpiler_options_schema）
- 驱动基类新增input_constrains和transpiler_options_schema属性，
  用于声明调度约束和转译器选项schema
- DriverGateBase声明通用transpiler_options_schema
  （optimization_level、enable_na_move、na_mapping_type、
  enable_mapping、sc_mapping_options、enable_wirecut）
- DriverLogicalQubitBase声明job_shots约束(1~50000)和
  enable_mapping约束(仅允许True)
- DriverQuafu声明job_shots约束(1024~102400，须为1024倍数)
  和enable_mapping约束(True/False均可)
- get-job-status命令支持"last"特殊值，自动解析最近作业的状态
- 支持Metrics容器(Prometheus、Alertmanager、Grafana)自动部署
- 新增worker的看门狗机制, 可以检查各组件健康状态并自动重启
- 新增支持ASHN门的Qutip模拟器

### 变更功能

- submit_job接口的backend参数改为可选，为空时触发自动调度
- CLI中所有可追加参数（--property、--device、--role-name）从action="append"改为nargs="+"形式
- 解决prefect-server内存泄露问题: 1. prefect升级到3.7.8;
  2\. 默认配置PREFECT_SERVER_DOCKET_URL为redis://IP:PORT/1
- 自动调度器_build_device_states注入availability_hourly和availability_total
  到DeviceState，供DeviceAvailabilityWeigher和DeviceAvailabilityFilter使用
- DEFAULT_FILTERS追加DeviceGroupFilter，统一通过BaseFilterHandler注入
  device_group_manager，不再特殊化处理
- DEFAULT_WEIGHERS追加DeviceAvailabilityWeigher
- 数据库时间统一为本地时间（datetime.now），移除所有datetime.utcnow
- DeviceState的set_availability合并为一个方法，参数availability_hourly
  和availability_total均可选（None表示不变）
- GateFidelityFilter处理fidelity返回None的情况，无数据时不阻塞设备
- DeviceGroupFilter改用spec.device_groups属性（支持extra_specs覆盖flavor）
- TechTypeFilter改用qc:tech_types多值匹配，修复key不匹配bug
- CodeTypeFilter支持qcos:code_types覆盖job的code_type约束
- FlavorManager的EXTRA_PROPERTY常量复用FlavorConstant，保持单一真相源
- ENABLED_FILTERS配置补充DeviceNameFilter和DeviceAvailabilityWeigher
- 代码命名统一：uptime_rate→availability相关命名（字段、方法、类、文件名）
- RequestSpec新增device_groups/tech_types/code_types/devices/exclude_devices
  属性，extra_specs覆盖flavor同名字段
- device_availability_hourly表的created_at/updated_at/hour改为本地时间，
  迁移脚本server_default改为NOW()
- webui/src/api/目录重构：device/driver/transpiler/job/version等6个API文件
  统一使用jsonrpcRequest/httpRequest封装
- webui/src/下所有.js文件添加版权头
- 自动调度器availability计算逻辑抽取到DeviceAvailabilityCollector
  .compute_availability_rates统一方法，auto_scheduler和device.py共用
- DriverWuyueBase和DriverLogicalQubitBase继承关系从DriverBase
  改为DriverGateBase，统一使用DriverGateBase的transpiler_options_schema
- driver_run统一调用post_run(driver)处理sleep/进度逻辑，
  各驱动不再自行实现set_progress_by_task(TASK_STAGE_COMPLETE)
- init_transpiler新增从driver.transpiler_options_schema填充
  转译器选项默认值的逻辑，用户未指定的选项自动使用schema声明的default
- submit_job路由将shots、circuit_aggregation、driver_options、
  transpiler_options传入build_request_spec，供调度器过滤使用
- DEFAULT_FILTERS追加InputConstraintsFilter，位于QueueLimitFilter之后
- DeviceState新增input_constrains、enable_circuit_aggregation、
  driver_options_schema、transpiler_options_schema字段，从driver属性映射

### 修复问题

- 无

### 移除内容

- 无

## [1.5.0] - 2026-06-24

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
