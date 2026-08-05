# qcos-decompose 介绍

qcos-decompose 是五岳量子计算操作系统（QCOS）的量子电路分解工具包，提供 OpenQASM 电路解析与门分解功能。

## 功能

- **QASM 解析**：将 OpenQASM 2.0 字符串解析为中间表示（IR）
- **门分解**：将电路中的量子门分解为目标基础门集合
- **QASM 导出**：将分解后的电路导出为 OpenQASM 2.0 字符串

## 安装

```bash
pip install qcos_decompose-0.1.0-py3-none-any.whl
```

## 使用

```python
from qcos_decompose import decompose_qasm

qasm_str = """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""

result = decompose_qasm(qasm_str, ["rx", "ry", "rz", "cx"])
print(result)
```

## 构建

```bash
cd build-scripts/sdk/qcos_decompose
bash build-wheel.sh
```

构建产物位于 `dist/` 目录下。

qcos-decompose 开源代码遵循 [MulanPSL-2.0](LICENSE) 开源协议。
