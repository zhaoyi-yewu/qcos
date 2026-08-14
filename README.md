# WUYUEQbit量子计算操作系统（QCOS）介绍

[![qcos](https://img.shields.io/docker/v/qcos/qcos/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos)](https://hub.docker.com/r/qcos/qcos-sandbox)
[![qcos-cli](https://img.shields.io/docker/v/qcos/qcos-cli/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos-cli)](https://hub.docker.com/r/qcos/qcos-sandbox)
[![qcos-sandbox](https://img.shields.io/docker/v/qcos/qcos-sandbox/latest?logo=docker&logoColor=2496ED&labelColor=white&label=qcos-sandbox)](https://hub.docker.com/r/qcos/qcos-sandbox)

[![PyPI - Version](https://img.shields.io/pypi/v/wy-qcos?logo=pypi&logoColor=white)](https://pypi.org/project/wy-qcos)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/wy-qcos?logo=python&logoColor=white)](https://pypi.org/project/wy-qcos)
[![JENKINS CICD](http://39.155.148.150:8080/job/WuYueOS-CICD-Daily/badge/icon?subject=jenkins/cicd)](http://39.155.148.150:8080/job/WuYueOS-CICD-Daily/)
[![GITHUB CICD](https://img.shields.io/github/actions/workflow/status/zhaoyi-yewu/qcos/qcos-cicd.yml?logo=githubactions&logoColor=white&labelColor=blue&label=github/cicd)](https://github.com/zhaoyi-yewu/qcos/actions/workflows/qcos-cicd.yml)
[![Codecov](https://codecov.io/github/zhaoyi-yewu/qcos/branch/develop/graph/badge.svg)](https://codecov.io/github/zhaoyi-yewu/qcos)
[![Documentation Status](https://app.readthedocs.org/projects/qcos/badge/?version=latest&style=plastic)](https://qcos.readthedocs.io/zh-cn/latest/)
[![License](https://img.shields.io/crates/l/efi_signer?logo=opensourceinitiative)](https://gitee.com/WUYUEQbit/qcos/blob/develop/LICENSE)

WUYUEQbit量子计算操作系统：QCOS（Quantum Computing Operating System）是一款开源的通用量子计算操作系统，旨在为不同架构的量子计算机（如：超导、中性原子、离子阱、相干伊辛机等）提供统一的软件支持，推动量子计算的生态发展。

## 1. 架构总览

![架构图](https://qcos.readthedocs.io/zh-cn/latest/_images/architecture.svg)

## 2. 功能特性

| 类别 | 功能 |
|:---------|:--------------------------------------------------------------------------------------|
| 交互方式 | 命令行、API、SDK、GUI（规划） |
| 系统服务 | 配置管理、日志管理、用户管理、监控告警、运维调试 |
| 设备管理 | 校准操作（规划）、设备配置/查询、设备可用率统计 |
| 作业管理 | 作业提交、取消、删除、状态查询、结果查询、自动调度 |
| 调度策略 | Flavor预设策略、设备分组、自动调度（Filter+Weigher）、extra_specs动态约束 |
| 量子引擎 | QASM解析、逻辑门分解、量子比特映射、编译优化、线路聚合、线路拆分、量子纠错QEC（规划） |
| 驱动插件 | 各类超导、中性原子、离子阱、光量子以及模拟器等，详见量子硬件兼容性说明 |

## 3. 安装使用

官方已适配操作系统：BCLinux 21.10U4、OpenEuler 24.03 (LTS)

**ReadTheDocs在线文档:** [https://qcos.readthedocs.io](https://qcos.readthedocs.io)

## 3.1 编译部署手册

[编译部署（基于Docker，推荐）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-docker.html)

[编译部署（基于K8s）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-k8s.html)

[编译部署（基于wheel）](https://qcos.readthedocs.io/zh-cn/latest/user-guide/deploy-guide/build-run-wheel.html)

## 3.2 命令行手册

[命令行手册](https://qcos.readthedocs.io/zh-cn/latest/user-guide/cli/index.html)

## 4. 兼容性说明

[软硬件执行环境](https://qcos.readthedocs.io/zh-cn/latest/user-guide/compatibility.html#%E8%BF%90%E8%A1%8C%E7%8E%AF%E5%A2%83%E5%85%BC%E5%AE%B9%E6%80%A7)
[量子设备兼容性](https://qcos.readthedocs.io/zh-cn/latest/user-guide/compatibility.html#%E7%9C%9F%E6%9C%BA%E6%B5%8B%E6%8E%A7%E9%A9%B1%E5%8A%A8%E5%85%BC%E5%AE%B9%E6%80%A7)

## 5. 许可证

QCOS开源代码遵循[MulanPSL-2.0](https://qcos.readthedocs.io/zh-cn/latest/other-docs/license.html)开源协议。
samples/qasm下的代码遵循 Apache-2.0开源协议。

## 6. 引用来源

### 6.1 QCOS中benchmark的公共测试集来源

- [benchpress](https://github.com/Qiskit/benchpress)
- [MQT QMAP](https://github.com/munich-quantum-toolkit/qmap)
