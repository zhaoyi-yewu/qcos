聚合与拆分
===================

本章节主要介绍了量子线路聚合与拆分、QUBO分解的设计。

量子线路聚合
--------------------
量子线路聚合的功能是将多个量子线路聚合成一个量子线路，通过聚合减少编译和执行开销，降低用户等待时间，提高系统整体并发量和效率。

(1)关键概念

量子线路聚合支持三种模式：

- **None模式** (AGGREGATION_TYPE_NONE)：不进行聚合，每个源码单独编译执行，结果直接返回
- **Internal模式** (AGGREGATION_TYPE_INTERNAL)：作业内聚合。
  单个Flow中多个源码编译为一个量子线路，执行后按原源码个数分割结果返回
- **External模式** (AGGREGATION_TYPE_EXTERNAL)：作业间聚合。
  多个Flow（父作业流/Parent + 子作业流/Sub）通过Prefect的暂停/恢复机制协调执行，父作业流编译聚合所有源码，执行后将结果分割返回给各子作业流

(2)关键数据结构

.. code-block:: python

    class AggregationInput(RunInput):
        """Prefect pause_flow_run等待的输入数据结构"""
        is_parent: bool              # 标记是否为Parent Flow
        sub_jobs: dict | None        # Sub Flow的参数字典，key为job_id，value为job_info
        sub_results: list[Any] | None  # Sub Flow的执行结果

    class SourceCodeInfo:
        """源码信息和聚合元数据"""
        aggregation_type: str           # 聚合类型：None/internal/external
        src_code_list: list[dict]      # 源码列表，每个元素为{job_id-index: source_code}的字典
        sub_flow_list: list[str]       # External模式下的Sub Flow ID列表

| aggregation_type: 聚合类型，取值为None、internal或external
| src_code_list: 源码组织方式。None模式每个源码单独成字典；internal/external模式多个源码按MAX_AGGREGATION_JOBS限制最大分组
| sub_flow_list: External模式下追踪的Sub Flow ID列表，用于最后的取消操作

(3)三种聚合模式的实现

**None模式流程：**

1. create_src_code_info(): 遍历每个源码，创建独立的{job_id-index: source_code}字典
2. run_code(): 逐个执行每个源码，返回单个job_results
3. 结果处理：job_results直接添加到job_results_list

**Internal模式流程：**

1. create_src_code_info(): 将源码按MAX_AGGREGATION_JOBS分组，每组作为一个{job_id-index: source_code}字典
2. run_code(): 每组源码聚合编译为单个量子线路，执行一次获得聚合结果
3. get_internal_aggregated_results():

   - 使用mapping_dict（记录每个源码对应的qubit数）和split_dict()分割结果
   - 为每个源码创建独立的job_results副本，填入对应的results子集
   - 返回结果列表

4. 结果处理：extend()添加所有分割后的结果到job_results_list

**External模式流程（关键的多Flow协调）：**

1. **提交阶段（task_manager）：**

   - 调用process_aggregation_job()启动监听线程
   - 监听Redis中以REDIS_CHANNEL_JOB_AGG_PREFIX前缀的消息

2. **Parent Flow暂停阶段（job_engine）：**

   - create_src_code_info(): 创建单个src_code_list，待后续更新
   - 发送flow_agg_info到Redis，携带flow_run_id和aggregation_type
   - 调用pause_flow_run(wait_for_input=AggregationInput)暂停，等待aggregation_info

3. **Task Manager匹配Sub Jobs（task_manager._process_aggregation_job）：**

   - 查询所有SCHEDULED状态且tags=[AGGREGATION_TYPE_EXTERNAL]的Flow
   - 匹配条件：

     - circuit_aggregation == external
     - backend相同
     - work_pool_name相同
     - 数量 < MAX_AGGREGATION_JOBS

   - 将匹配的sub flow的参数构建为AggregationInput.sub_jobs
   - 轮询检查Parent是否已进入PAUSED状态（最多等待JOB_AGG_FLOW_PAUSE_WAIT_TIMEOUT秒）
   - 调用resume_flow_run(flow_run_id, run_input=aggregation_params)恢复Parent，
     其中aggregation_params为{"is_parent": True, "sub_jobs": {...}}

4. **Parent Flow恢复执行（job_engine）：**

   - aggregation_info = pause_flow_run()返回（包含sub_jobs映射）
   - 检查is_parent：为False则返回（Sub Job处理），为True则继续
   - update_src_code_info(): 将Sub Jobs的源码添加到src_code_info.src_code_list，并追踪sub_flow_list
   - 执行run_code()，编译所有源码（Parent+Sub）聚合为单个量子线路

5. **结果处理（job_engine）：**

   - get_external_aggregated_results():

     - 使用mapping_dict记录的job_id与qubit数映射分割结果
     - 第一个（Parent）的结果保留在job_results中
     - 其余（Sub）的结果组织为sub_results字典，key为job_id，value为该Sub的job_results副本
     - 返回包含sub_results的merged job_results

   - 发送flow_agg_info到Redis，携带cancel=True和sub_flow_list，通知Task Manager取消Sub Flow

6. **Sub Job处理（job_engine）：**

   - Sub Job暂停后aggregation_info.is_parent=False，直接返回None
   - Sub Job的结果通过db_job_callback在数据库层处理

(4)三种聚合模式总体对比

以下是三种聚合模式的并行流程对比：

.. plantuml:: ../../_static/design/module-design/circuit-aggregation-overview.puml
   :caption: 三种模式的流程对比（包图）
   :alt: 三种模式的流程对比
   :width: 100%
   :align: center

(5)聚合模式决策流程

系统根据circuit_aggregation参数进行模式选择：

.. plantuml:: ../../_static/design/module-design/circuit-aggregation.puml
   :caption: 聚合模式选择决策流程
   :alt: 聚合模式选择决策流程
   :width: 100%
   :align: center

(6)详细流程图

下图展示三种模式的完整执行流程，包含环节分组和参与者职责：

.. plantuml:: ../../_static/design/module-design/circuit-aggregation-flow.puml
   :caption: 量子线路聚合三种模式详细流程图
   :alt: 量子线路聚合三种模式详细流程图
   :width: 100%
   :align: center

(7)External模式协调时序图

External模式的关键是多Flow之间的协调。以下时序图展示了Parent和Sub Flow的完整交互过程：

.. plantuml:: ../../_static/design/module-design/circuit-aggregation-external.puml
   :caption: External模式多Flow协调时序图
   :alt: External模式多Flow协调时序图
   :width: 100%
   :align: center

(8)关键算法与设计细节

**split_dict() - 按Qubit边界分割结果**

利用mapping_dict记录的qubit count信息，将测量结果按bitstring长度分割：

.. code-block:: python

    # 输入：orig_dict = {"00": 100, "01": 50, "10": 30, "11": 20}
    #       mapping_dict = {job0: 2, job1: 2}  # 各占2个qubit
    #       split_len = [2, 2]
    # split_dict按第一维(index 0-1)、第二维(index 2-3)分割key
    # 输出结果列表，每个元素对应一个job的bitstring

**get_internal_aggregated_results() - 内聚合结果分割**

- 输入作业聚合执行的结果 + mapping_dict
- 处理：使用split_dict分割，为每个源码创建独立副本
- 输出：结果列表，列表长度 = src_code_list长度

**get_external_aggregated_results() - 外聚合结果处理**

- 输入：聚合执行的结果 + mapping_dict（包含Parent+Sub）
- 处理：

  1. 使用split_dict分割
  2. 第一个结果保留为Parent的job_results
  3. 其余结果组织为sub_results字典
  4. Sub Job的job_id通过job_id.rsplit("-", 1)[0]还原

- 输出：单个merged job_results，包含results和sub_results

**与DB更新的集成**

- Parent result: 直接写入DB，job_status=COMPLETED
- Sub results: 通过db_job_callback()在result中传递，DB层merge处理
- 故障场景：Parent失败 → 所有Sub自动取消；Sub开始前被取消 → Parent发送cancel信号

(9)约束与限制

- MAX_AGGREGATION_JOBS: 单次聚合的最大job数量
- JOB_AGG_FLOW_PAUSE_WAIT_TIMEOUT: Parent暂停最长等待时间（10秒）
- External模式Sub必须与Parent backend/pool相同
- Internal模式多个源码编译为单个线路，要求门集兼容
- 不支持嵌套聚合（子聚合作业不能再聚合）

量子线路拆分
--------------------

量子线路拆分目的是解决通用量子计算机受限于量子比特数量，无法直接求解大电路问题而设计的。
支持将用户提交的大电路作业分解为量子计算机能够支持最大比特规模的一系列子电路作业，
经过量子计算机求解后重构为大电路的执行结果。

大电路作业通过电路拆分再求解的具体流程：

|   1、作业提交：用户提交电路作业，系统构建相应的作业流（job_flow）
|   2、规模判定：工作流管理组件电路大小
|   (1)若电路比特未超限（满足设备比特要求）：直接向设备提交作业求解，直接跳转步骤6
|   (2)若电路比特超限：进入电路分解流程
|   3、电路分解：工作流管理组件先将电路转为DAG图，然后进行电路切割
|   4、子电路求解：将子电路作业提交至设备求解
|   5、概率分布重构：合并所有子电路的结果，进行概率分布重构
|   6、结果返回：流程终止后，用户通过原作业ID(job_id)从结果接口获取最终概率分布结果。

电路切割时序图：

.. plantuml:: ../../_static/design/module-design/circuit-cutting.puml
   :caption: 电路切割时序图
   :alt: 电路切割时序图
   :width: 80%
   :align: center

QUBO分解
--------------------

QUBO拆分（也称QUBO分解）目的是解决伊辛机受限于量子比特数量，无法直接求解大QUBO问题而设计的。
支持将用户提交的大QUBO作业分解为伊辛机能够支持最大比特规模的子QUBO作业，
并基于QUBO分解算法进行解的合并于重构，结合优化更新算法最终获取最优解。

大QUBO作业通过QUBO分解算法求解问题的具体流程：

|   1、作业提交：用户提交QUBO的量子作业，系统构建相应的作业流（job_flow）
|   2、规模判定：工作流管理组件校验QUBO问题规模
|   （1）若规模未超限（满足伊辛机比特要求）：直接向设备提交作业求解，跳转步骤7
|   （2）若规模超限：进入大QUBO分解流程
|   3、QUBO分解：工作流管理组件调用QUBO分解算法，将原问题分解为符合伊辛机比特数限制的子QUBO问题（subQUBO）
|   4、子作业求解：将subQUBO作业提交至伊辛机进行求解，并收集返回的中间解
|   5、解合并与重构：工作流管理组件基于分解规则，将subQUBO求解的解合并，重构出原大规模QUBO的一个候选完整解
|   6、收敛性判断：根据预设的优化更新算法判断解是否收敛：
|   （1）若未收敛：流程结束进入步骤7
|   （2）若收敛：以当前解为新的起点，返回步骤3，启动新一轮分解与求解，进行迭代优化。
|   7、结果返回：流程终止后，用户通过原作业ID(job_id)从结果接口获取最终求解结果。

QUBO分解时序图：

.. plantuml:: ../../_static/design/module-design/qubo-cutting.puml
   :caption: QUBO分解时序图
   :alt: QUBO分解时序图
   :width: 80%
   :align: center
