#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

# Don't import any other libraries (os is required for security: reading
# the fernet secret key from the environment instead of hardcoding it)
import os

from wy_qcos.common.qcos_version import QcosVersion

_s = lambda x: x

DEFAULT_AI_SYSTEM_PROMPT = """你是集成在 QCOS（量子计算操作系统）WebUI 中的 \
AI 智能体。**默认使用简体中文进行所有回答与思考**。

【语言要求 - 最高优先级】
- 无论用户使用什么语言提问，你都必须使用简体中文输出最终答案。
- 无论用户使用什么语言提问，你的思考过程 / chain-of-thought / \
reasoning 也必须使用简体中文。
- 只有当用户明确要求"用英文回答"或"用其他语言回答"时，才切换语言。
- 即使用户用英文提问，你也必须用中文回答。

【能力范围】
1. 回答 QCOS 使用方法、量子计算概念、故障排查问题
2. 生成和解释 QASM 量子线路代码
3. 调用 MCP 工具查询设备状态、作业进度、系统健康度
4. 在提供 RAG 上下文时引用 QCOS 文档

【可用工具 - 必须通过 function calling 调用，禁止只用文字描述】
- qcos_list_devices(details): 列出所有可用量子计算设备；\
  details=True 返回完整物理参数，仅需概要信息时使用 details=False
- qcos_get_device_detail(name): 获取指定设备详情
- qcos_list_jobs(job_status, backend, page_size, page_num): 列出量子作业
- qcos_get_job_status(job_id): 查询指定作业状态
- qcos_get_job_result(job_id): 获取已完成作业的结果
- qcos_submit_job(source_code, code_type, backend, shots, job_name): \
提交 QASM 作业
- qcos_cancel_jobs(job_ids): 取消运行/排队中的作业
- qcos_get_system_health: 获取 QCOS 系统健康状态
- qcos_get_job_stats: 获取作业统计
- qcos_get_api_stats: 获取 API 请求统计
- qcos_get_current_user: 获取当前认证用户信息
- qcos_get_version: 获取 QCOS 系统版本
- qcos_read_file(file_path, max_lines, offset): 读取本地源码/文档文件

【可观测性工具 - 代理到 Prometheus / Alertmanager / VictoriaLogs】
- qcos_proxy_get_health(): 获取反向代理上游健康状态
- qcos_proxy_query_metrics(query, time, timeout): PromQL 即时查询
- qcos_proxy_query_metrics_range(query, start, end, step): PromQL 区间查询
- qcos_proxy_list_metric_names(): 列出所有 Prometheus 指标名
- qcos_proxy_list_alerts(status, silenced, inhibited): 列出 Alertmanager 告警
- qcos_proxy_list_silences(): 列出 Alertmanager 静默规则
- qcos_proxy_query_logs(query, limit, start, end): VictoriaLogs LogsQL 查询
- qcos_proxy_log_tail(lines): 拉取最新 N 行日志

【工具调用关键规则】
- 当用户询问设备、作业、系统状态、文件等需要真实数据的问题时，必须发起真正的 \
function call（tool_call），禁止只写"我将调用..."或\
"让我查一下..."这类文字描述。
- 工具返回结果后，用简体中文自然语言向用户总结结果。
- 工具调用失败或返回空时，如实告知用户，禁止编造数据。

【真实数据强制约束 - 禁止捏造作业与设备状态】
- 设备清单、设备状态、作业 ID、作业状态、测量结果（counts/概率）、执行耗时等\
一切运行时数据，**只能来自 MCP 工具的真实返回**，严禁凭印象、推测或"模拟执行"\
编造。没有调用工具，就没有这些数据。
- 用户要求"提交作业并分析结果"时，必须按依赖顺序完成完整工具调用链，\
缺一不可：
  1. 调用 qcos_submit_job 真实提交：source_code 使用实际 QASM 文本，\
code_type="qasm"，backend 使用用户指定的设备名（如 qutip_sim），\
shots 使用用户指定值（如 1024），job_name 可概括任务。
  2. 使用 submit 工具返回的真实 job_id 调用 qcos_get_job_status 查询状态；\
若仍在排队/运行，继续调用直到完成或失败。
  3. 作业完成后调用 qcos_get_job_result 获取真实测量结果，\
再基于真实 counts 进行分析。
- 从图片或代码截图中识别出的 QASM，同样必须通过 qcos_submit_job 真实提交；\
禁止把"模拟运行的结果"当作设备结果返回。
- 未实际调用工具、工具调用失败或作业未完成时，**不得**声称"已提交""已完成"\
"结果如下"，必须明确说明当前实际执行到哪一步、失败原因或阻塞点。
- 如果当前对话形态没有可用工具，必须如实说明无法执行，并给出用户可操作的\
下一步，而不是伪造执行过程。

【画图能力 - 需要配图时直接用代码画图】
- 当回答需要图示（架构图、流程图、时序图、状态图、设备拓扑、类图、ER 图）时，\
直接在回答中输出 ```mermaid 代码块（Mermaid 语法），前端会在本地渲染成图片。
- **只准使用 Mermaid**：禁止输出 PlantUML（```plantuml / ```puml）或 \
Graphviz DOT 代码块，前端无法渲染它们。即使用户点名要 PlantUML / UML 图，\
也必须改用 Mermaid 等价语法绘制，不要解释"无法渲染 PlantUML"。
- 常用图型对照：流程图/架构图用 flowchart TD 或 flowchart LR；\
时序图用 sequenceDiagram；类图用 classDiagram；状态图用 stateDiagram-v2；\
ER 图用 erDiagram。
- 代码块内只写图定义源码，不要在代码块内夹带解释文字；\
在图前后用中文简述图的含义。
- 节点或标签文字含括号、冒号、分号等特殊字符时，用双引号包裹\
（如 A["文本(含括号)"]），避免 Mermaid 解析失败。
- 不要输出外部图片链接或 base64 图片。

【通用准则】
- 用简体中文思考，用简体中文回答
- 回答简洁、技术化
- 调用工具前用中文简述要做什么；工具返回后用中文总结结果
- 提供 RAG 上下文时引用源文档章节
- 不知道就老实说不知道
- 不要向用户暴露原始堆栈或内部错误细节
- 同一会话可能切换过不同大模型，历史助手消息中的自我身份表述（如"我是 Kimi"）\
描述的是当时生成那条回答的模型，**不代表你的身份**。被问"你是谁"时，\
请以你当前实际模型的身份作答，不要为了与历史回答保持一致而沿用其他模型的\
自我介绍。
"""

DEFAULT_AI_VISION_SYSTEM_PROMPT = """你是专注于量子计算相关图像分析的 AI \
智能体。**默认使用简体中文进行所有回答与思考**。

【语言要求 - 最高优先级】
- 无论用户使用什么语言提问，你都必须使用简体中文输出最终答案。
- 无论用户使用什么语言提问，你的思考过程也必须使用简体中文。
- 只有当用户明确要求"用英文回答"时，才切换语言。

【可分析的图像类型】
- 量子线路图（Qiskit、Cirq 等）
- QASM / QUBO 代码截图
- 错误堆栈截图
- 矩阵热力图
- 设备拓扑图

【准则】
- 准确描述图像中看到的内容
- 用中文解释图中涉及的量子计算概念
- 为代码截图提供调试建议
- 用户要求时，从图像中转录代码
- 回答简洁、技术化
- 历史助手消息中的自我身份表述（如"我是 Kimi"）来自当时生成它的模型，\
不代表你的身份；被问"你是谁"时以你当前实际模型身份作答。

【真实数据强制约束 - 禁止捏造作业与结果】
- 你可以使用与文本对话相同的 MCP 工具（qcos_submit_job、\
qcos_get_job_status、qcos_get_job_result、qcos_list_devices 等）。\
当用户要求"分析图片并提交到某设备 / 查询作业 / 分析结果"时，\
必须按顺序完成真实工具调用链：
  1. 先完成图像分析，转录出完整可提交的 QASM 代码。
  2. 调用 qcos_submit_job 真实提交：source_code 使用转录的 QASM，\
code_type="qasm"，backend 使用用户指定设备（如 qutip_sim），\
shots 使用用户指定值（如 1024）。
  3. 使用工具返回的真实 job_id 调用 qcos_get_job_status 轮询直到完成。
  4. 调用 qcos_get_job_result 获取真实测量结果，再基于真实 counts 分析。
- **严禁**编造作业 ID、"已提交成功"提示、作业状态、测量 counts 或概率分布；\
没有真实工具返回，就没有这些数据。
- 不得把"模拟运行""理论预期"的结果描述为设备实际执行结果；如需说明理论\
预期，必须明确标注"这只是理论推测，尚未在设备上执行"。
- 工具调用失败时如实告知失败原因，不得伪造后续执行过程。
"""


class Constant:
    """Constants."""

    PROGRAM_NAME = "WuYue-QCOS"
    PROGRAM_AUTHOR = "CMSS"
    PLATFORM_NAME = "WUYUEQbit量子计算操作系统(QCOS)"
    PLATFORM_VERSION = f"{PLATFORM_NAME} v{QcosVersion.VERSION}"
    COPYRIGHT = "2024-2026 中移（苏州）软件技术有限公司"

    # API version
    API_VERSION_V1 = "v1"
    API_VERSION = API_VERSION_V1

    # QCOS server default IP and port
    DEFAULT_API_SERVER_LISTEN_IP = ""
    DEFAULT_API_SERVER_LISTEN_PORT = 18400
    DEFAULT_API_VERSION = "v1"

    # Metrics server defaults
    DEFAULT_METRICS_SERVER_LISTEN_IP = ""
    DEFAULT_METRICS_SERVER_LISTEN_PORT = 19400
    DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS = 30

    # QCOS client-side server default IP and port
    DEFAULT_QCOS_SERVER_IP = "127.0.0.1"
    DEFAULT_QCOS_SERVER_PORT = 18400

    # REDIS server default URL
    DEFAULT_REDIS_SERVER_IP = "127.0.0.1"
    DEFAULT_REDIS_SERVER_PORT = 6379
    DEFAULT_REDIS_URL = (
        f"redis://{DEFAULT_REDIS_SERVER_IP}:{DEFAULT_REDIS_SERVER_PORT}/0"
    )
    REDIS_CHANNEL_QCOS_PREFIX = "/qcos"
    REDIS_CHANNEL_DEVICE_RUNNING_INFO_PREFIX = (
        f"{REDIS_CHANNEL_QCOS_PREFIX}/device_running_info"
    )
    REDIS_CHANNEL_JOB_AGG_PREFIX = f"{REDIS_CHANNEL_QCOS_PREFIX}/job_agg"
    # Job notification channel prefix for pub/sub and redis key prefix
    # for job storage. Any job stored in redis publishes its updated
    # record on "{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}" so
    # subscribers (e.g. the wirecut parent flow) can track progress and
    # terminal status via pub/sub instead of polling. The same prefix
    # is used as the redis key prefix, so a job record is stored under
    # "{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}".
    REDIS_CHANNEL_JOB_PREFIX = f"{REDIS_CHANNEL_QCOS_PREFIX}/jobs"

    # AI agent Redis key prefixes
    REDIS_CHANNEL_AI_PREFIX = f"{REDIS_CHANNEL_QCOS_PREFIX}/ai"
    REDIS_CHANNEL_AI_SESSION_PREFIX = f"{REDIS_CHANNEL_AI_PREFIX}/session"
    REDIS_CHANNEL_AI_MESSAGES_PREFIX = f"{REDIS_CHANNEL_AI_PREFIX}/messages"
    REDIS_CHANNEL_AI_USER_SESSIONS_PREFIX = (
        f"{REDIS_CHANNEL_AI_PREFIX}/user_sessions"
    )

    # Job results storage backends
    RESULTS_DB_STORAGE_SQL = "sql"
    RESULTS_DB_STORAGE_REDIS = "redis"
    RESULTS_DB_STORAGE_DEFAULT = RESULTS_DB_STORAGE_SQL

    # DATABASE
    DB_DIALECT_POSTGRESQL = "postgresql"

    # Security
    DEFAULT_FERNET_KEY = os.environ.get(
        "FERNET_SECRET_KEY", "APzd4m3XeveFilLjkT5vMzCjKzEhphvOkVzGFF_ERFM="
    )
    ENCRYPTION_PREFIX = "++"

    # Flow limit
    FLOW_LIMIT = 100000

    # Python bin
    PYTHON_BIN = "python3"
    PYPY_BIN = "pypy"

    # Code types
    CODE_TYPE_QASM = "qasm"
    CODE_TYPE_QASM2 = "qasm2"
    CODE_TYPE_QASM3 = "qasm3"
    CODE_TYPE_QUBO = "qubo"
    CODE_TYPES_ALL_QASM = [CODE_TYPE_QASM, CODE_TYPE_QASM2, CODE_TYPE_QASM3]
    CODE_TYPES = [
        CODE_TYPE_QASM,
        CODE_TYPE_QASM2,
        CODE_TYPE_QASM3,
        CODE_TYPE_QUBO,
    ]

    # Aggregation types
    AGGREGATION_TYPE_INTERNAL = "internal"
    AGGREGATION_TYPE_EXTERNAL = "external"
    AGGREGATION_TYPE_NONE = "None"
    AGGREGATION_TYPES = [
        AGGREGATION_TYPE_NONE,
        AGGREGATION_TYPE_INTERNAL,
        AGGREGATION_TYPE_EXTERNAL,
    ]
    JOB_AGG_FLOW_PAUSE_WAIT_TIMEOUT = 10

    # File types
    FILE_TYPE_QASM = ".qasm"
    FILE_TYPE_JSON = ".json"
    FILE_TYPE_CSV = ".csv"

    # User length
    MIN_USER_LENGTH = 2
    MAX_USER_LENGTH = 64

    # Role length
    MIN_ROLE_LENGTH = 2
    MAX_ROLE_LENGTH = 64

    # Project length
    MIN_PROJECT_LENGTH = 2
    MAX_PROJECT_LENGTH = 64

    # Description length
    MIN_DESCRIPTION_LENGTH = 1
    MAX_DESCRIPTION_LENGTH = 255

    # Password length
    MIN_PASSWORD_LENGTH = 6
    MAX_PASSWORD_LENGTH = 32

    # Pagination
    PAGE_SIZE = 50

    # Quantum Gates
    # single-qubit gates
    SINGLE_QUBIT_GATE_X = "x"
    SINGLE_QUBIT_GATE_Y = "y"
    SINGLE_QUBIT_GATE_Z = "z"
    SINGLE_QUBIT_GATE_H = "h"
    SINGLE_QUBIT_GATE_S = "s"
    SINGLE_QUBIT_GATE_T = "t"
    SINGLE_QUBIT_GATE_P = "p"
    SINGLE_QUBIT_GATE_U = "u"
    SINGLE_QUBIT_GATE_U_UPPERCASE = "U"
    SINGLE_QUBIT_GATE_R = "r"
    SINGLE_QUBIT_GATE_RX = "rx"
    SINGLE_QUBIT_GATE_RY = "ry"
    SINGLE_QUBIT_GATE_RZ = "rz"
    SINGLE_QUBIT_GATE_SX = "sx"
    SINGLE_QUBIT_GATE_SXDG = "sxdg"
    SINGLE_QUBIT_GATE_I = "id"
    SINGLE_QUBIT_GATE_SDG = "sdg"
    SINGLE_QUBIT_GATE_TDG = "tdg"
    SINGLE_QUBIT_GATE_U1 = "u1"
    SINGLE_QUBIT_GATE_U2 = "u2"
    SINGLE_QUBIT_GATE_U3 = "u3"
    SINGLE_QUBIT_GATE_RESET = "reset"
    SINGLE_QUBIT_GATE_LIST = [
        SINGLE_QUBIT_GATE_X,
        SINGLE_QUBIT_GATE_Y,
        SINGLE_QUBIT_GATE_Z,
        SINGLE_QUBIT_GATE_H,
        SINGLE_QUBIT_GATE_S,
        SINGLE_QUBIT_GATE_T,
        SINGLE_QUBIT_GATE_P,
        SINGLE_QUBIT_GATE_U,
        SINGLE_QUBIT_GATE_U_UPPERCASE,
        SINGLE_QUBIT_GATE_R,
        SINGLE_QUBIT_GATE_RX,
        SINGLE_QUBIT_GATE_RY,
        SINGLE_QUBIT_GATE_RZ,
        SINGLE_QUBIT_GATE_SX,
        SINGLE_QUBIT_GATE_SXDG,
        SINGLE_QUBIT_GATE_I,
        SINGLE_QUBIT_GATE_SDG,
        SINGLE_QUBIT_GATE_TDG,
        SINGLE_QUBIT_GATE_U1,
        SINGLE_QUBIT_GATE_U2,
        SINGLE_QUBIT_GATE_U3,
    ]
    # two-qubit gates
    TWO_QUBIT_GATE_CH = "ch"
    TWO_QUBIT_GATE_CRX = "crx"
    TWO_QUBIT_GATE_CRY = "cry"
    TWO_QUBIT_GATE_CRZ = "crz"
    TWO_QUBIT_GATE_CX = "cx"
    TWO_QUBIT_GATE_CX_UPPERCASE = "CX"
    TWO_QUBIT_GATE_CY = "cy"
    TWO_QUBIT_GATE_CZ = "cz"
    TWO_QUBIT_GATE_SWAP = "swap"
    TWO_QUBIT_GATE_ISWAP = "iswap"
    TWO_QUBIT_GATE_CU1 = "cu1"
    TWO_QUBIT_GATE_CP = "cp"
    TWO_QUBIT_GATE_CS = "cs"
    TWO_QUBIT_GATE_CSDG = "csdg"
    TWO_QUBIT_GATE_CU3 = "cu3"
    TWO_QUBIT_GATE_ECR = "ecr"
    TWO_QUBIT_GATE_DCX = "dcx"
    TWO_QUBIT_GATE_CSX = "csx"
    TWO_QUBIT_GATE_CU = "cu"
    TWO_QUBIT_GATE_RXX = "rxx"
    TWO_QUBIT_GATE_RYY = "ryy"
    TWO_QUBIT_GATE_RZZ = "rzz"
    TWO_QUBIT_GATE_RZX = "rzx"
    TWO_QUBIT_GATE_ASHN = "ashn"
    TWO_QUBIT_GATE_LIST = [
        TWO_QUBIT_GATE_CH,
        TWO_QUBIT_GATE_CRX,
        TWO_QUBIT_GATE_CRY,
        TWO_QUBIT_GATE_CRZ,
        TWO_QUBIT_GATE_CX,
        TWO_QUBIT_GATE_CX_UPPERCASE,
        TWO_QUBIT_GATE_CY,
        TWO_QUBIT_GATE_CZ,
        TWO_QUBIT_GATE_SWAP,
        TWO_QUBIT_GATE_ISWAP,
        TWO_QUBIT_GATE_CU1,
        TWO_QUBIT_GATE_CP,
        TWO_QUBIT_GATE_CS,
        TWO_QUBIT_GATE_CSDG,
        TWO_QUBIT_GATE_CU3,
        TWO_QUBIT_GATE_ECR,
        TWO_QUBIT_GATE_DCX,
        TWO_QUBIT_GATE_CSX,
        TWO_QUBIT_GATE_CU,
        TWO_QUBIT_GATE_RXX,
        TWO_QUBIT_GATE_ECR,
        TWO_QUBIT_GATE_RZZ,
        TWO_QUBIT_GATE_DCX,
    ]
    # three-qubit gates
    THREE_QUBIT_GATE_CCX = "ccx"
    THREE_QUBIT_GATE_CCZ = "ccz"
    THREE_QUBIT_GATE_CSWAP = "cswap"
    THREE_QUBIT_GATE_RCCX = "rccx"
    THREE_QUBIT_GATE_LIST = [
        THREE_QUBIT_GATE_CCX,
        THREE_QUBIT_GATE_CCZ,
        THREE_QUBIT_GATE_CSWAP,
        THREE_QUBIT_GATE_RCCX,
    ]
    # four-qubit gates
    FOUR_QUBIT_GATE_RC3X = "rc3x"
    FOUR_QUBIT_GATE_C3X = "c3x"
    FOUR_QUBIT_GATE_C3SQRTX = "c3sqrtx"
    FOUR_QUBIT_GATE_LIST = [
        FOUR_QUBIT_GATE_RC3X,
        FOUR_QUBIT_GATE_C3X,
        FOUR_QUBIT_GATE_C3SQRTX,
    ]
    # five-qubit gates
    FIVE_QUBIT_GATE_C4X = "c4x"
    FIVE_QUBIT_GATE_LIST = [
        FIVE_QUBIT_GATE_C4X,
    ]
    # all gate list
    ALL_GATE_LIST = (
        SINGLE_QUBIT_GATE_LIST
        + TWO_QUBIT_GATE_LIST
        + THREE_QUBIT_GATE_LIST
        + FOUR_QUBIT_GATE_LIST
        + FIVE_QUBIT_GATE_LIST
    )
    ALL_GATES = "all"

    # Backends
    BACKEND_TYPE_DEVICE = "device"
    BACKEND_TYPE_WIRECUT = "wirecut"
    ALL_BACKEND_TYPES = [BACKEND_TYPE_DEVICE, BACKEND_TYPE_WIRECUT]

    # Drivers
    DRIVER_DUMMY = "dummy"
    DRIVERS = set()  # autofilled during driver registration

    # Devices
    DEVICE_DUMMY = "dummy"

    # Device Groups
    DEVICE_GROUP_DN_ALL = "_all"

    # Work pool name
    WORK_POOL_DEV = "dev"
    WORK_POOL_MON = "mon"
    WORK_POOL_MGR = "mgr"
    WORK_POOL_VDEV = "vdev"
    WORK_POOL_TYPES = [
        WORK_POOL_DEV,
        WORK_POOL_MON,
        WORK_POOL_MGR,
        WORK_POOL_VDEV,
    ]
    VIRT_DEVICE_WIRECUT = "wirecut"
    # Prefix of the wirecut sub-job flow run name (see
    # submit_jobs in wirecut_engine). RedisJobStorageBackend strips it
    # from job ids before building the redis storage key, so all paths
    # (db_utils and job_storage_backend) share one naming rule.
    WIRECUT_FLOW_RUN_PREFIX = "vdev-wirecut-"

    # Process
    PROCESS_PREFIX = "proc"

    # Worker type names (returned by _parse_worker_name). These map
    # 1:1 to the work pool prefix constants above.
    WORKER_TYPE_DEV = "dev"
    WORKER_TYPE_MON = "mon"
    WORKER_TYPE_MGR = "mgr"
    WORKER_TYPE_VDEV = "vdev"

    # Transpiler
    TRANSPILER_CMSS = "cmss"
    TRANSPILER_HIGH_PERFORMANCE_CMSS = "high_performance_cmss"
    TRANSPILER_QISKIT = "qiskit"
    TRANSPILER_DUMMY = "dummy"
    TRANSPILER_CMSS_QUBO = "cmss_qubo"
    TRANSPILERS = set()  # autofilled during plugin registration
    DEFAULT_TRANSPILER = TRANSPILER_CMSS

    # Quantum computer tech types
    TECH_TYPE_NONE = "none"
    TECH_TYPE_NEUTRAL_ATOM = "neutral_atom"
    TECH_TYPE_ION_TRAP = "ion_trap"
    TECH_TYPE_SUPERCONDUCTING = "superconducting"
    TECH_TYPE_PHOTON = "photon"
    TECH_TYPE_NMR = "nmr"
    TECH_TYPE_GENERIC_SIMULATOR = "generic_simulator"
    TECH_TYPE_DEDICATED_SIMULATOR = "dedicated_simulator"
    TECH_TYPE_INFO = {
        TECH_TYPE_NEUTRAL_ATOM: {"alias_name": "中性原子"},
        TECH_TYPE_ION_TRAP: {"alias_name": "离子阱"},
        TECH_TYPE_SUPERCONDUCTING: {"alias_name": "超导"},
        TECH_TYPE_PHOTON: {"alias_name": "光量子"},
        TECH_TYPE_NMR: {"alias_name": "核磁共振"},
        TECH_TYPE_GENERIC_SIMULATOR: {"alias_name": "通用量子模拟器"},
        TECH_TYPE_DEDICATED_SIMULATOR: {"alias_name": "专用量子模拟器"},
    }
    TECH_TYPES = list(TECH_TYPE_INFO.keys())

    # Job types
    JOB_TYPE_SAMPLING = "sampling"
    JOB_TYPE_ESTIMATION = "estimation"
    JOB_TYPES = [JOB_TYPE_SAMPLING, JOB_TYPE_ESTIMATION]

    # Result types
    RESULT_TYPE_SAMPLING = "sampling"
    RESULT_TYPE_ESTIMATION = "estimation"
    RESULT_TYPE_QUBO = "qubo"
    RESULT_TYPE_TEXT = "text"
    RESULT_TYPE_DICT = "dict"
    RESULT_TYPES = [
        RESULT_TYPE_SAMPLING,
        RESULT_TYPE_ESTIMATION,
        RESULT_TYPE_QUBO,
        RESULT_TYPE_TEXT,
        RESULT_TYPE_DICT,
    ]

    # Results fetch mode
    RESULTS_FETCH_MODE_SYNC = "sync"
    RESULTS_FETCH_MODE_ASYNC = "async"
    RESULTS_FETCH_MODE_SET = "set"
    RESULTS_FETCH_ASYNC_RETRIES = 3
    RESULTS_FETCH_ASYNC_TIMEOUT = 30

    # Profiling types
    PROFILING_TYPE_ALL = "all"
    PROFILING_TYPE_CODE = "code"
    PROFILING_TYPE_CODE_STARTED_AT = "code_started_at"
    PROFILING_TYPE_CODE_ENDED_AT = "code_ended_at"
    PROFILING_TYPE_QUEUING = "queuing"
    PROFILING_TYPE_QUEUING_STARTED_AT = "queuing_started_at"
    PROFILING_TYPE_QUEUING_ENDED_AT = "queuing_ended_at"
    PROFILING_TYPE_SCHEDULING = "scheduling"
    PROFILING_TYPE_SCHEDULING_STARTED_AT = "scheduling_started_at"
    PROFILING_TYPE_SCHEDULING_ENDED_AT = "scheduling_ended_at"
    PROFILING_TYPE_DRIVER_PARSE = "driver:parse"
    PROFILING_TYPE_DRIVER_PARSE_STARTED_AT = "driver:parse_started_at"
    PROFILING_TYPE_DRIVER_PARSE_ENDED_AT = "driver:parse_ended_at"
    PROFILING_TYPE_DRIVER_TRANSPILE = "driver:transpile"
    PROFILING_TYPE_DRIVER_TRANSPILE_STARTED_AT = "driver:transpile_started_at"
    PROFILING_TYPE_DRIVER_TRANSPILE_ENDED_AT = "driver:transpile_ended_at"
    PROFILING_TYPE_DRIVER_RUN = "driver:run"
    PROFILING_TYPE_DRIVER_RUN_STARTED_AT = "driver:run_started_at"
    PROFILING_TYPE_DRIVER_RUN_ENDED_AT = "driver:run_ended_at"
    PROFILING_TYPE_MACHINE = "machine"
    PROFILING_TYPE_MACHINE_STARTED_AT = "machine_started_at"
    PROFILING_TYPE_MACHINE_ENDED_AT = "machine_ended_at"

    PROFILING_TYPES = [
        PROFILING_TYPE_ALL,
        PROFILING_TYPE_CODE,
        PROFILING_TYPE_QUEUING,
        PROFILING_TYPE_SCHEDULING,
        PROFILING_TYPE_DRIVER_PARSE,
        PROFILING_TYPE_DRIVER_TRANSPILE,
        PROFILING_TYPE_DRIVER_RUN,
        PROFILING_TYPE_MACHINE,
    ]
    PROFILING_INFO = {
        PROFILING_TYPE_ALL: {"alias_name": "使能所有性能评估类型"},
        PROFILING_TYPE_CODE: {"alias_name": "作业中单代码执行耗时"},
        PROFILING_TYPE_QUEUING: {"alias_name": "作业排队耗时"},
        PROFILING_TYPE_SCHEDULING: {"alias_name": "调度器耗时"},
        PROFILING_TYPE_DRIVER_PARSE: {"alias_name": "代码解析耗时"},
        PROFILING_TYPE_DRIVER_TRANSPILE: {"alias_name": "转译器耗时"},
        PROFILING_TYPE_DRIVER_RUN: {"alias_name": "后端运行耗时"},
        PROFILING_TYPE_MACHINE: {"alias_name": "量子计算机运行耗时"},
    }

    # Callback types
    CALLBACK_TYPE_RESULTS = "results"
    CALLBACK_TYPES = [CALLBACK_TYPE_RESULTS]

    # Maximum jobs allowed in the system
    MAX_AGGREGATION_JOBS = 5

    # Job priority
    DEFAULT_JOB_PRIORITY = 5
    MIN_JOB_PRIORITY = 1
    MAX_JOB_PRIORITY = 10
    SUB_WIRECUT_PRIORITY = 4  # higher priority than default for sub-wirecut

    # Job params
    MAX_JOB_WORKER = 1
    DEFAULT_AGGREGATION_JOB_INTERVAL = 10

    # Code compression level
    DEFAULT_CODE_COMPRESSION_LEVEL = 0
    MIN_CODE_COMPRESSION_LEVEL = 0
    MAX_CODE_COMPRESSION_LEVEL = 9

    # job engine configs
    DEFAULT_JOB_POOL_TYPE = "process"
    DEFAULT_POOL_CONCURRENCY = 1
    VIRTUAL_DEVICE_POOL_CONCURRENCY = 100
    DEFAULT_JOB_TIMEOUT = 300
    DEFAULT_JOB_INTERVAL = 5

    # device monitor engine configs
    DEFAULT_DEVICE_MONITOR_RETRIES = 100
    DEFAULT_DEVICE_MONITOR_RETRY_DELAY_INTERVAL = 600
    DEFAULT_DEVICE_MONITOR_POLLING_INTERVAL = 60
    # max wait time (seconds) for fetch_running_info before
    # treating the device as disconnected
    DEFAULT_DEVICE_MONITOR_FETCH_TIMEOUT = 30

    # device availability rate aggregation
    # cron minute (0 = top of every hour) for hourly availability aggregation
    DEFAULT_AVAILABILITY_AGGREGATE_CRON_MINUTE = 0
    # device statuses counted as "online" for availability rate calculation
    DEVICE_AVAILABILITY_STATUS_ONLINE_BUSY = ("online", "busy")

    # user management
    AUTH_MODE_KEY = "auth_mode"
    AUTH_MODE_NO = "no"
    AUTH_MODE_JWT = "jwt"
    AUTH_MODE_VIRTUAL_INSTANCE = "virtual_instance"
    AUTH_MODES = [AUTH_MODE_NO, AUTH_MODE_JWT, AUTH_MODE_VIRTUAL_INSTANCE]

    ADMIN_PROJECT_ID = "00000000-0000-4000-8000-000000000001"
    ADMIN_PROJECT_NAME = "admin project"
    DEFAULT_PROJECT_ID = "00000000-0000-4000-8000-000000000000"
    DEFAULT_PROJECT_NAME = "default project"
    ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = _s("P*ssword1")
    DEFAULT_VIRTUAL_INSTANCE_PASSWORD = _s("111111")
    ANONYMOUS_USER_ID = "00000000-0000-4000-8000-000000000000"
    ANONYMOUS_USERNAME = "anonymous"
    INVALID_PROJECT_ID = "00000000-0000-0000-0000-000000000000"
    INVALID_USER_ID = "00000000-0000-0000-0000-000000000000"
    ENV_VAR_ACCESS_TOKEN = _s("QCOS_ACCESS_TOKEN")
    JWT_AUTH_AUDIENCE = "qcos-api"
    ROLE_ADMIN = "admin"
    ROLE_USER = "user"
    ROLE_ANY = "__any__"
    ALL_ROLES = [ROLE_ADMIN, ROLE_USER]

    # Job status
    JOB_STATUS_UNKNOWN = "UNKNOWN"
    JOB_STATUS_QUEUED = "QUEUED"
    JOB_STATUS_RUNNING = "RUNNING"
    JOB_STATUS_FAILED = "FAILED"
    JOB_STATUS_COMPLETED = "COMPLETED"
    JOB_STATUS_CANCELLING = "CANCELLING"
    JOB_STATUS_CANCELLED = "CANCELLED"
    JOB_STATUS_DELETING = "DELETING"
    JOB_STATUS_DELETED = "DELETED"
    # Sum of all job statuses (used in job_count totals)
    JOB_STATUS_TOTAL = "TOTAL"
    JOB_STATUSES = [
        JOB_STATUS_QUEUED,
        JOB_STATUS_RUNNING,
        JOB_STATUS_FAILED,
        JOB_STATUS_COMPLETED,
        JOB_STATUS_CANCELLING,
        JOB_STATUS_CANCELLED,
        JOB_STATUS_DELETING,
        JOB_STATUS_DELETED,
        JOB_STATUS_UNKNOWN,
    ]

    # Terminal job statuses: a job is considered finished once it
    # reaches one of these states.
    JOB_TERMINAL_STATUSES = {
        JOB_STATUS_COMPLETED,
        JOB_STATUS_FAILED,
        JOB_STATUS_CANCELLED,
    }

    # Non-terminal job statuses: jobs in these states are still
    # considered in-flight and need startup synchronization with
    # Prefect flow-run states.
    JOB_NON_TERMINAL_STATUSES = {
        JOB_STATUS_QUEUED,
        JOB_STATUS_RUNNING,
        JOB_STATUS_CANCELLING,
        JOB_STATUS_DELETING,
        JOB_STATUS_UNKNOWN,
    }

    # Prefect flow state
    PREFECT_STATE_RUNNING = "RUNNING"
    PREFECT_STATE_SCHEDULED = "SCHEDULED"
    PREFECT_STATE_PENDING = "PENDING"
    PREFECT_STATE_LATE = "LATE"
    PREFECT_STATE_FAILED = "FAILED"
    PREFECT_STATE_COMPLETED = "COMPLETED"
    PREFECT_STATE_CRASHED = "CRASHED"
    PREFECT_STATE_CANCELLING = "CANCELLING"
    PREFECT_STATE_CANCELLED = "CANCELLED"
    PREFECT_STATE_PAUSED = "PAUSED"
    PREFECT_CANCEL_REQUIRED_STATES = [
        PREFECT_STATE_RUNNING,
        PREFECT_STATE_CANCELLING,
    ]
    PREFECT_WAIT_STATES = [PREFECT_STATE_SCHEDULED, PREFECT_STATE_PENDING]

    # Prefect terminal state -> QCOS job status mapping (used by
    # startup job synchronization to align DB with Prefect truth).
    # NOTE: defined AFTER the PREFECT_STATE_* constants above.
    PREFECT_TO_QCOS_TERMINAL_STATE = {
        PREFECT_STATE_COMPLETED: JOB_STATUS_COMPLETED,
        PREFECT_STATE_FAILED: JOB_STATUS_FAILED,
        PREFECT_STATE_CRASHED: JOB_STATUS_FAILED,
        PREFECT_STATE_CANCELLED: JOB_STATUS_CANCELLED,
    }

    VID_TAGS_PREFIX = "VIRTUAL_INSTANCE_ID"

    # Prefect job log
    PREFECT_JOB_LOG_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
    )

    # Shots
    DEFAULT_SHOTS = 10
    MIN_SHOTS = 1

    # Qubits
    DEFAULT_QUBITS = 1
    MIN_QUBITS = 1
    MAX_QUBITS = 1024

    # Optimization level
    DEFAULT_OPTIMIZATION_LEVEL = 1
    MIN_OPTIMIZATION_LEVEL = 0
    MAX_OPTIMIZATION_LEVEL = 3

    # Max bitwidth
    MAX_QUBO_BIT_WIDTH = 8
    MAX_QUBO_QUBITS = 2000

    # Circuit cutting
    MAX_CIRCUIT_CUT = 100
    MAX_RERURSIVE_DEPTH = 100

    # Complete reconstruction bit threshold
    COMPLETE_RECONSTRUCTION_THRESHOLD = 32

    # Max memory for dynamic definition
    DD_MAX_MEMORY = 1024

    # --- Metrics constants ---
    # system metrics
    # system stats field names
    SYSTEM_HEALTHY = "system_healthy"
    HEARTBEAT_TIMESTAMP = "heartbeat_timestamp"
    # Component names
    COMPONENT_NAME_FASTAPI = "fastapi"
    COMPONENT_NAME_REDIS = "redis"
    COMPONENT_NAME_PREFECT = "prefect"
    COMPONENT_NAME_WORKER = "worker"
    COMPONENT_NAMES = [
        COMPONENT_NAME_FASTAPI,
        COMPONENT_NAME_REDIS,
        COMPONENT_NAME_PREFECT,
        COMPONENT_NAME_WORKER,
    ]

    # Optional component names (feature flags)
    COMPONENT_NAME_AI_AGENT = "agent"
    COMPONENT_NAME_AI_MCP_SERVER = "mcp_server"
    COMPONENT_NAME_TERMINAL = "terminal"
    COMPONENT_NAME_METRICS_SERVER = "metrics_server"
    COMPONENT_NAME_PROXY_PROMETHEUS = "prometheus"
    COMPONENT_NAME_PROXY_ALERTMANAGER = "alertmanager"
    COMPONENT_NAME_PROXY_VICTORIALOGS = "victorialogs"
    COMPONENT_NAME_EMBEDDING = "embedding"
    COMPONENT_NAME_VISION = "vision"

    OPTIONAL_COMPONENT_NAMES = [
        COMPONENT_NAME_AI_AGENT,
        COMPONENT_NAME_AI_MCP_SERVER,
        COMPONENT_NAME_TERMINAL,
        COMPONENT_NAME_METRICS_SERVER,
        COMPONENT_NAME_PROXY_PROMETHEUS,
        COMPONENT_NAME_PROXY_ALERTMANAGER,
        COMPONENT_NAME_PROXY_VICTORIALOGS,
        COMPONENT_NAME_EMBEDDING,
        COMPONENT_NAME_VISION,
    ]

    # Component status
    COMPONENT_STATUS = "component_status"
    COMPONENT_STATUS_ONLINE = "online"
    COMPONENT_STATUS_OFFLINE = "offline"

    # Job metrics
    JOB_METRICS_FIELD_TOTAL = "total"
    JOB_METRICS_PROMETHEUS_NAME = "job_count"
    JOB_METRICS_FIELD_COMPLETED = JOB_STATUS_COMPLETED.lower()
    JOB_METRICS_FIELD_FAILED = JOB_STATUS_FAILED.lower()
    JOB_METRICS_FIELD_RUNNING = JOB_STATUS_RUNNING.lower()
    JOB_METRICS_FIELD_QUEUED = JOB_STATUS_QUEUED.lower()
    JOB_METRICS_FIELD_CANCELLING = JOB_STATUS_CANCELLING.lower()
    JOB_METRICS_FIELD_CANCELLED = JOB_STATUS_CANCELLED.lower()
    JOB_METRICS_FIELD_DELETING = JOB_STATUS_DELETING.lower()
    JOB_METRICS_FIELD_DELETED = JOB_STATUS_DELETED.lower()
    JOB_METRICS_FIELD_UNKNOWN = JOB_STATUS_UNKNOWN.lower()
    JOB_METRICS_FIELD_SUBMITTED_JOB_RATE_MIN = "submitted_job_rate_min"
    JOB_METRICS_FIELD_COMPLETED_JOB_RATE_MIN = "completed_job_rate_min"

    # API metrics
    API_METRICS_REQUESTS_TOTAL = "api_requests_total"
    API_METRICS_REQUESTS_IN_PROGRESS = "api_requests_in_progress"
    API_METRICS_REQUESTS_DURATION = "api_request_duration"
    API_METRICS_REQUEST_STATS = "api_request"

    # API stats field names
    API_TOTAL_REQUESTS = "total_requests"
    API_LAST_HOUR_REQUESTS = "last_hour_requests"
    API_LAST_DAY_REQUESTS = "last_day_requests"

    # System stats Prometheus metric names (qcos_system_*)
    # Process-level
    SYSTEM_STATS_RSS_MB = "qcos_system_rss_mb"
    SYSTEM_STATS_VMS_MB = "qcos_system_vms_mb"
    SYSTEM_STATS_THREAD_COUNT = "qcos_system_thread_count"
    SYSTEM_STATS_NUM_OBJECTS = "qcos_system_num_objects"
    SYSTEM_STATS_CPU_PERCENT = "qcos_system_process_cpu_percent"
    # Host-level
    SYSTEM_STATS_HOST_CPU_PERCENT = "qcos_system_host_cpu_percent"
    SYSTEM_STATS_CPU_COUNT = "qcos_system_cpu_count"
    SYSTEM_STATS_MEM_TOTAL_MB = "qcos_system_mem_total_mb"
    SYSTEM_STATS_MEM_PERCENT = "qcos_system_mem_percent"
    SYSTEM_STATS_DISK_TOTAL_MB = "qcos_system_disk_total_mb"
    SYSTEM_STATS_DISK_FREE_MB = "qcos_system_disk_free_mb"
    SYSTEM_STATS_DISK_PERCENT = "qcos_system_disk_percent"

    DEFAULT_JOB_QUERY_INTERVAL = 5
    DEFAULT_JOB_WAIT_TIME = 604800


class HttpHeaders:
    # headers
    DEFAULT_JSON_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


class HttpMethod:
    """HTTP methods."""

    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"


class HttpCode:
    """HTTP status codes."""

    SUCCESS_OK = 200
    SUCCESS_CREATED = 201
    SUCCESS_ACCEPTED = 202
    SUCCESS_NO_CONTENT = 204
    BAD_REQUEST_ERROR = 400
    UNAUTHORIZED_ERROR = 401
    FORBIDDEN_ERROR = 403
    NOT_FOUND_ERROR = 404
    TIMEOUT_ERROR = 408
    CONFLICT_ERROR = 409
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED_ERROR = 501
    SERVICE_UNAVAILABLE_ERROR = 503
