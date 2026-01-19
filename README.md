# 五岳量子计算操作系统（QCOS）介绍

五岳量子计算操作系统：QCOS（Quantum Computing Operating System）是一款开源的通用量子计算操作系统，旨在为不同架构的量子计算机（如：超导、中性原子、离子阱、相干伊辛机等）提供统一的软件支持，推动量子计算的生态发展。

# 1. 架构总览

![架构图](./docs/sphinx/source/_static/architecture.png)

# 2. 功能特性

| | 功能 |
|:-----|:------------------------------------:|
| 交互方式 | 命令行、API、SDK、GUI（规划） |
| 系统服务 | 配置管理、日志管理、用户管理（规划）、权限管理（规划）、监控管理（规划） |
| 设备管理 | 校准操作（规划）、设备配置/查询 |
| 作业管理 | 作业提交、取消、删除、状态查询、结果查询 |
| 系统引擎 | QASM解析、逻辑门分解、量子比特映射、编译优化、线路聚合、线路拆分（规划）、量子纠错QEC（规划） |
| 驱动插件 | dummy测试驱动、光量子、中性原子、超导、离子阱等 |

# 3. 安装使用

官方已适配操作系统：BCLinux 21.10U4

**ReadTheDocs在线文档:** [https://qcos.readthedocs.io](https://qcos.readthedocs.io)

## 3.1 编译部署手册

[编译部署（基于Docker，推荐）](docs/sphinx/source/user-guide/deploy-guide/build-run-docker.rst)

[编译部署（基于K8s）](docs/sphinx/source/user-guide/deploy-guide/build-run-k8s.rst)

[编译部署（基于wheel）](docs/sphinx/source/user-guide/deploy-guide/build-run-wheel.rst)

## 3.2 命令行手册

[命令行手册](docs/sphinx/source/user-guide/cli.rst)

## 3.3 文档构建手册

[文档构建手册](docs/sphinx/source/user-guide/deploy-guide/build-docs.rst)

# 4. 兼容性

[兼容性说明](COMPATIBILITY.md)

# 5. 许可证

QCOS开源代码遵循[MulanPSL-2.0](LICENSE)开源协议。
samples/qasm下的代码遵循 Apache-2.0开源协议。
