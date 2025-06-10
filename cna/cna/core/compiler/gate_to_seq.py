from ..pulse import *
import numpy as np
import json


def gate_to_seq(gates, qpu_file=None):
    """
    将中间表示（门表示）转换到脉冲序列上

    参数:
    gates (_type_): 门列表
    qpu_file (str): 配置文件路径
    返回:
    Tuple (list, list): 脉冲序列、测量比特列表
    """
    config = {}
    if qpu_file is not None:
        with open(qpu_file, 'r') as f:
            config = json.loads(f.read())['raman']

    pi_length = config.get('c3_time', 12e-6) * 1e6
    pulse_seqs = []
    measure_qubits = []
    for gate in gates:
        if gate.name == 'rx':
            dura = abs(gate.arg_value[0]) / np.pi * pi_length
            pulse_seqs.append(Raman(dura, amp=0, freq=0, phase=0.0).on(gate.targets))
        elif gate.name == 'ry':
            dura = abs(gate.arg_value[0]) / np.pi * pi_length
            pulse_seqs.append(Raman(dura, amp=0, freq=0, phase=np.pi / 2).on(gate.targets))
        elif gate.name == 'rz':
            pass
        elif gate.name == 'cx':
            param_dict = {
                'ion_number': 2,
                'segment_number': 3,
                'time_intervals': [(0, 17.33), (17.33, 45.66), (45.66, 87.99)],
                'data_per_ion': {
                    # 第一个比特的参数表
                    gate.targets[0]: {
                        'amp': [(0.45, 0.45), (0.42, 0.42), (0.23, 0.23)],
                        'freq': [(4 + 2.03, 4 - 2.03), (4 + 2.03, 4 - 2.03), (4 + 2.03, 4 - 2.03)],
                        'phase': [(0.48, -0.48), (0.308, -0.308), (0.086, -0.086)]
                    },
                    # 第二个比特的参数表
                    gate.targets[1]: {
                        'amp': [(0.42, 0.42), (0.23, 0.23), (0.45, 0.45, 0.10)],
                        'freq': [(4 + 2.03, 4 - 2.03), (4 + 2.03, 4 - 2.03), (4 + 2.03, 4 - 2.03, 2.03)],
                        'phase': [(0.308, -0.308), (0.086, -0.086), (-0.086, 0.086, 0.086)]
                    }
                }
            }
            pulse_seqs.append(
                MolmerSorensen(para_table=param_dict).on(gate.targets)
            )
        elif gate.name == 'measure':
            measure_qubits += gate.targets
        elif gate.name == 'sync':
            pulse_seqs.append(sync(gate.targets))
        elif gate.name == 'mov':
            continue
        else:
            raise TypeError(f'{gate.name} cannot be converted to pulses')
    if measure_qubits:
        if len(measure_qubits) > 0:
            pulse_seqs.append(sync(measure_qubits))
        pulse_seqs.append(Detection(duration=100).on(measure_qubits))
    return pulse_seqs, measure_qubits
