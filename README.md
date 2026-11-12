# WUYUEQbit量子计算操作系统（QCOS）介绍

[<img alt="qcos" src="https://img.shields.io/docker/v/qcos/qcos/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos&style=flat" height="20" style="vertical-align:middle;">](https://hub.docker.com/r/qcos/qcos)
[<img alt="qcos-cli" src="https://img.shields.io/docker/v/qcos/qcos-cli/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos-cli&style=flat" height="20" style="vertical-align:middle;">](https://hub.docker.com/r/qcos/qcos-cli)
[<img alt="qcos-webui" src="https://img.shields.io/docker/v/qcos/qcos-webui/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos-webui&style=flat" height="20" style="vertical-align:middle;">](https://hub.docker.com/r/qcos/qcos-webui)
[<img alt="qcos-sandbox" src="https://img.shields.io/docker/v/qcos/qcos-sandbox/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos-sandbox&style=flat" height="20" style="vertical-align:middle;">](https://hub.docker.com/r/qcos/qcos-sandbox)
<br>
[<img alt="PyPI - Version" src="https://img.shields.io/pypi/v/wy-qcos?logo=pypi&logoColor=white&style=flat" height="20" style="vertical-align:middle;">](https://pypi.org/project/wy-qcos)
[<img alt="PyPI - Wheel" src="https://img.shields.io/pypi/wheel/wy-qcos?logo=python&logoColor=white&style=flat" height="20" style="vertical-align:middle;">](https://pypi.org/project/wy-qcos)
[<img alt="MCP Server" src="https://img.shields.io/badge/MCP-Server-black?logo=modelcontextprotocol&style=flat" height="20" style="vertical-align:middle;">](https://qcos.readthedocs.io/zh-cn/latest/user-guide/mcp/mcp.html)
[<img alt="AI Agent Chat" src="https://img.shields.io/badge/AI_Agent-Chat_Enabled-brightgreen?logo=probot&logoColor=white&style=flat" height="20" style="vertical-align:middle;">](https://qcos.readthedocs.io/zh-cn/latest/user-guide/ai-agent.html)
[<img alt="License" src="https://img.shields.io/badge/license-MulanPSL--2.0-blue?logo=opensourceinitiative&style=flat" height="20" style="vertical-align:middle;">](https://gitee.com/WUYUEQbit/qcos/blob/develop/LICENSE)
<br>
[<img alt="Codecov" src="https://img.shields.io/codecov/c/github/zhaoyi-yewu/qcos?branch=develop&style=flat" height="20" style="vertical-align:middle;">](https://codecov.io/github/zhaoyi-yewu/qcos)
[<img alt="Documentation Status" src="https://img.shields.io/readthedocs/qcos/latest?style=flat" height="20" style="vertical-align:middle;">](https://qcos.readthedocs.io/zh-cn/latest/)
[<img alt="GITHUB CICD" src="https://img.shields.io/github/actions/workflow/status/zhaoyi-yewu/qcos/qcos-cicd.yml?logo=githubactions&logoColor=white&labelColor=blue&label=github/cicd&style=flat" height="20" style="vertical-align:middle;">](https://github.com/zhaoyi-yewu/qcos/actions/workflows/qcos-cicd.yml)
[<img alt="JENKINS CICD" src="https://img.shields.io/badge/jenkins/cicd-failing-orange?style=flat" height="20" style="vertical-align:middle;">](http://39.155.148.150:8080/job/WuYueOS-CICD-Daily/badge/icon?subject=jenkins/cicd)

WUYUEQbit量子计算操作系统：QCOS（Quantum Computing Operating System）是一款开源的通用量子计算操作系统，旨在为不同架构的量子计算机（如：超导、中性原子、离子阱、相干伊辛机等）提供统一的软件支持，推动量子计算的生态发展。

## 1. 架构总览

![架构图](https://qcos.readthedocs.io/zh-cn/latest/_images/architecture.svg)

## 2. 功能特性

| 类别 | 功能 |
|:------|:------------------------------------------------------------------------------------------------------------------------------|
| 交互方式 | 命令行、API、SDK、WEBUI、AI-Agent 协议：AG-UI（over SSE）、MCP（over Streamable HTTP） |
| 用户管理 | 多租户隔离、多用户、RBAC（基于角色的）API 权限控制、JWT登录认证 |
| 设备管理 | 校准操作（规划）、设备配置/查询、设备可用率统计 |
| 作业管理 | 作业提交、取消、删除、状态查询、结果查询、自动调度 |
| 自动调度 | Flavor预设调度策略、设备分组、过滤器Filter、权重器Weigher、extra_specs动态约束 |
| 作业引擎 | QASM解析、逻辑门分解、量子比特映射、编译优化、线路聚合、线路拆分、量子纠错QEC（规划） |
| 驱动插件 | 各类超导、中性原子、离子阱、光量子以及模拟器等，详见：[量子硬件兼容性说明](https://qcos.readthedocs.io/zh-cn/latest/user-guide/compatibility.html#qdevice-compat) |
| 系统服务 | 配置管理、日志管理、监控告警、运维调试 |
| 人工智能 | 多模型接入、RAG文档检索、MCP工具调用、源码只读问答、图片分析、SSE流式对话 |
| 监控告警 | 支持指标采集、告警、日志采集及可视化面板 |

## 3. 安装使用

官方已适配操作系统：BCLinux 21.10U4、OpenEuler 24.03 (LTS)

**ReadTheDocs在线文档:** [https://qcos.readthedocs.io](https://qcos.readthedocs.io)

## 3.1 编译部署手册

[编译部署（基于Docker，推荐）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-docker.html)

[编译部署（基于K8s）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-k8s.html)

[编译部署（基于wheel）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-wheel.html)

## 3.2 用户指导

[命令行手册](https://qcos.readthedocs.io/zh-cn/latest/user-guide/cli/index.html)

[场景介绍和操作](https://qcos.readthedocs.io/zh-cn/latest/user-guide/scenario/index.html)

[Python客户端](https://qcos.readthedocs.io/zh-cn/latest/user-guide/sdk.html)

[运维指导](https://qcos.readthedocs.io/zh-cn/latest/user-guide/operations.html)

## 4. 兼容性说明

[软硬件执行环境](https://qcos.readthedocs.io/zh-cn/latest/user-guide/compatibility.html#soft-env-compat)

[量子设备兼容性](https://qcos.readthedocs.io/zh-cn/latest/user-guide/compatibility.html#qdevice-compat)

## 5. 开发者指导

[开发环境搭建](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/developer-environment.html)

[代码开发流程](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/code-commit.html)

[新功能模块开发](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/develop-new-module.html)

[新量子设备驱动开发](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/develop-new-driver.html)

[新WebUI页面开发](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/develop-new-webui-page.html)

[调试指南](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/debug-guidelines.html)

[项目开发规范](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/developer-guidelines.html)

[测试和CICD](https://qcos.readthedocs.io/zh-cn/latest/developer-guide/run-tests.html)

## 6. 许可证

QCOS开源代码遵循[MulanPSL-2.0](https://qcos.readthedocs.io/zh-cn/latest/other-docs/license.html)开源协议。
samples/qasm下的代码遵循 Apache-2.0开源协议。

## 7. 引用来源

### 7.1 QCOS中benchmark的公共测试集来源

- [benchpress](https://github.com/Qiskit/benchpress)
- [MQT QMAP](https://github.com/munich-quantum-toolkit/qmap)
