# 运行环境兼容性

## 操作系统兼容性

| 系统 | 支持版本 | 测试状态 |
|:------|:----------------------------------------------|:-----|
| Linux | OpenEuler 24.03 (LTS) | 全量测试 |
| Linux | BigCloud Enterprise Linux For Euler 21.10 LTS | 全量测试 |

## 硬件资源要求

| CPU要求 | 内存要求 |
|:--------|:--------|
| x86_64 | >=128G |

## 编程语言/运行时

| 语言/运行时 | 支持版本 | 测试状态 |
|:-------|:-------|:-----|
| Python | 3.11.6 | 全量测试 |

# 真机/测控驱动兼容性

| 驱动名称 | 驱动类名 | 驱动版本 | 技术路线 | 最大量子比特数 | 转译器 | 驱动描述 |
|:-------------------------------|:-----------------------|:------|:-------|:--------|:-------|:------------------------------------|
| 空载测试驱动(中性原子) | DriverDummy | 0.0.1 | 中性原子 | 36 | cmss | 空载测试驱动(中性原子) |
| 中科酷原-汉原1 中性原子驱动 (FPGA) | DriverHanyuan1 | 0.0.1 | 中性原子 | 100 | cmss | 中科酷原-汉原1 中性原子驱动 (FPGA版) |
| 中科酷原-汉原1-Pulse 中性原子脉冲驱动| DriverHanyuan1Pulse | 0.0.1 | 中性原子 | 100 | cmss | 中科酷原-汉原1 中性原子脉冲驱动 |
| 量旋科技 大熊座-S25 超导量子计算机驱动 (RPC版本) | DriverSpinQRpc | 0.0.1 | 超导 | 57 | cmss | 量旋科技 大熊座-S25 超导量子计算机驱动 (RPC版本) (实验) |
| 量旋科技 双子座 核磁量子计算机驱动 | DriverSpinQGemini | 0.0.1 | 核磁共振 | 2 | dummy | 量旋科技 双子座 核磁量子计算机驱动 (实验) |
| 量旋科技 三角座 核磁量子计算机驱动 | DriverSpinQTriangulum | 0.0.1 | 核磁共振 | 2 | dummy | 量旋科技 三角座 核磁量子计算机驱动 (实验) |
| 幺正量子 UQC-Matrix2 离子阱驱动 | DriverUQCMatrix2 | 0.0.1 | 离子阱 | 5 | cmss | 幺正量子 UQC-Matrix2 离子阱驱动 |
| 五岳-中科酷原-汉原1 中性原子驱动 | DriverWuyueHanyuan1 | 0.0.1 | 中性原子 | 100 | cmss | 五岳-中科酷原-汉原1 中性原子驱动 (云平台版) |
| 五岳-中科酷原-汉原1 中性原子驱动 - 模拟器 | DriverWuyueHanyuan1Sim | 0.0.1 | 中性原子 | 25 | cmss | 五岳-中科酷原-汉原1 中性原子驱动 (云平台模拟器版) |
| Qiskit Aer 模拟器驱动 | DriverQiskitAerSim | 0.0.1 | 通用模拟器 | 30 | qiskit | Qiskit Aer 模拟器驱动 |
| Qiskit Qasm 模拟器驱动 | DriverQiskitQasmSim | 0.0.1 | 通用模拟器 | 30 | qiskit | Qiskit Qasm 模拟器驱动 |
| Qutip 模拟器驱动 | DriverQutipSim | 0.0.1 | 通用模拟器 | 10 | cmss | Qutip 模拟器驱动 |
| Quafu 超导驱动 | DriverQuafu | 0.0.1 | 超导 | 84 | cmss | Quafu 超导驱动 |
| Stim 仿真器驱动 | DriverStim | 0.0.1 | 专用仿真器 | 10 | cmss | Stim 仿真器驱动 |

上表也可以通过QCOS系统命令行查看：

```bash
# qcos-cli list-drivers
```

# 依赖库兼容性

参见requirements/目录依赖的Python第三方包版本，建议在容器环境或者venv虚拟环境下运行
