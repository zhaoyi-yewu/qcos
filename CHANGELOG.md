# QCOS Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - Work In Progress
### Added

## [1.0.0] - 2025-12-17
### Added
+ 支持命令行 (qcos-cli)
+ 支持JSON-RPC API
+ 支持作业提交、查询、删除、取消
+ 支持排队中的作业修改优先级
+ 支持用户提交作业时选择转译器, 可选择: 五岳转译器(cmss)、Qiskit转译器(qiskit)
+ 五岳转译器(cmss)支持QASM解析、逻辑门分解、量子比特映射、编译优化
+ 支持用户提交作业时选择后端驱动, 可选择: 测试驱动、中科酷原中性原子、玻色光量子伊辛机驱动等等
+ 支持多设备并行操作能力
+ 支持设备独立配置文件和查询能力
+ 支持作业运行各阶段性能评估数据获取(profiling)
+ 支持UT/ST
+ 支持容器化部署, 具备一键编译/运行脚本
+ 支持配置全局最大作业数、最大排队+运行作业数限制
+ 支持日志轮转配置: 最大日志文件大小、日志文件保留数量

### Changed
### Fixed
### Removed
