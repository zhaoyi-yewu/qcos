# 五岳量子计算操作系统（QCOS）介绍

[![qcos](https://img.shields.io/docker/v/qcos/qcos/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos)](https://hub.docker.com/r/qcos/qcos-sandbox)
[![qcos-cli](https://img.shields.io/docker/v/qcos/qcos-cli/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos-cli)](https://hub.docker.com/r/qcos/qcos-sandbox)
[![qcos-sandbox](https://img.shields.io/docker/v/qcos/qcos-sandbox/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos-sandbox)](https://hub.docker.com/r/qcos/qcos-sandbox)

[![PyPI - Version](https://img.shields.io/pypi/v/wy-qcos?logo=pypi&logoColor=white)](https://pypi.org/project/wy-qcos)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/wy-qcos?logo=python&logoColor=white)](https://pypi.org/project/wy-qcos)
[![CICD](https://img.shields.io/github/actions/workflow/status/zhaoyi-yewu/qcos/qcos-cicd.yml?logo=githubactions&logoColor=white&labelColor=blue&label=build/cicd)](https://github.com/zhaoyi-yewu/qcos/actions/workflows/qcos-cicd.yml)
[![Codecov](https://codecov.io/github/zhaoyi-yewu/qcos/branch/develop/graph/badge.svg)](https://codecov.io/github/zhaoyi-yewu/qcos)
[![Documentation Status](https://img.shields.io/readthedocs/qcos/latest?logo=readthedocs)](https://qcos.readthedocs.io/zh-cn/latest/)
[![License](https://img.shields.io/crates/l/efi_signer?logo=opensourceinitiative)](https://gitee.com/OpenWuYue/qcos/blob/develop/LICENSE)

五岳量子计算操作系统：QCOS（Quantum Computing Operating System）是一款开源的通用量子计算操作系统，旨在为不同架构的量子计算机（如：超导、中性原子、离子阱、相干伊辛机等）提供统一的软件支持，推动量子计算的生态发展。

# 1. 架构总览

![架构图](https://gitee.com/OpenWuYue/qcos/raw/develop/docs/sphinx/source/_static/architecture.svg)

# 2. 功能特性

| | 功能 |
|:-----------------------------------------------|:---------------------------------------------------|
| <span style="white-space:nowrap;">交互方式</span> | 命令行、API、SDK、GUI（规划） |
| <span style="white-space:nowrap;">系统服务</span> | 配置管理、日志管理、用户管理、监控告警（规划） |
| <span style="white-space:nowrap;">设备管理</span> | 校准操作（规划）、设备配置/查询 |
| <span style="white-space:nowrap;">作业管理</span> | 作业提交、取消、删除、状态查询、结果查询 |
| <span style="white-space:nowrap;">系统引擎</span> | QASM解析、逻辑门分解、量子比特映射、编译优化、线路聚合、线路拆分（规划）、量子纠错QEC（规划） |
| <span style="white-space:nowrap;">驱动插件</span> | dummy测试驱动、光量子、中性原子、超导、离子阱等 |

# 3. 安装使用

官方已适配操作系统：BCLinux 21.10U4

**ReadTheDocs在线文档:** [https://qcos.readthedocs.io](https://qcos.readthedocs.io)

## 3.1 编译部署手册

[编译部署（基于Docker，推荐）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-docker.html)

[编译部署（基于K8s）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-k8s.html)

[编译部署（基于wheel）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-wheel.html)

## 3.2 命令行手册

[命令行手册](https://qcos.readthedocs.io/zh-cn/latest/user-guide/cli.html)

# 4. 兼容性

[兼容性说明](https://qcos.readthedocs.io/zh-cn/latest/user-guide/compatibility.html)

# 5. 许可证

QCOS开源代码遵循[MulanPSL-2.0](https://qcos.readthedocs.io/zh-cn/latest/other-docs/license.html)开源协议。
samples/qasm下的代码遵循 Apache-2.0开源协议。
