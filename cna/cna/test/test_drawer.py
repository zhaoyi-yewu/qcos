from qcos.cna.core.gui import *

qasm = '''
OPENQASM 2.0;
include "qelib1.inc";

qreg q[2];
creg c[2];

u3(0.1, 0.2, 0.3) q[0];
cx q[0], q[1];
x q[0];
measure q->c;
'''
 
def test_circuit():
    c = get_circuit(qasm)
    assert len(c.operations) == 5
    d = c.operations[0].to_dict()
    assert d['targets'] == [0]
    assert c.operations[0].targets == [0] and c.operations[0].param == '(0.1,0.2,0.3)'
    assert c.operations[1].targets == [1] and c.operations[1].controls == [0]
    assert c.operations[2].targets == [0]
    assert c.operations[3].targets == [0] and c.operations[3].isMeasurement == True
    assert c.operations[4].targets == [1] and c.operations[4].isMeasurement == True
    d = c.to_dict()

def test_circuit_param():
    dic = {
    'qubits': ['Q1', 'Q4', 'Q5', 'Q6', 'Q7'],
    'operations': [
        {'gate': 'MX', 'targets': ['Q1', 'Q4']},
        {'gate': 'MH', 'targets': ['Q1', 'Q5']},
        {'gate': 'RX', 'targets': ['Q4'], 'param': '(0.5,0.6,0.7)'},
        {'gate': 'X', 'targets': ['Q4'], 'controls': ['Q1', 'Q7']},
        {'gate': 'M', 'targets': ['Q1'], 'isMeasurement': True, 'style': {'box_options': {'facecolor': '#FFDE86', 'edgecolor': 'black', 'linewidth': 1, 'zorder': 2}}},
        {'gate': 'X2M', 'targets': ['Q4']},
        {'gate': 'H', 'targets': ['Q5']},
        {'gate': 'Y', 'targets': ['Q6']},
        {'gate': 'Y', 'targets': ['Q6']},
        {'gate': 'Y', 'targets': ['Q6']}
    ],
    'max_circuit_depth': 10,
    'style': {
        'box_options': {'facecolor': '#D9F1FA', 'edgecolor': 'black', 'linewidth': 1, 'zorder': 2}
    },
    'show_param': True,
    'optimized': True,
    'show_label': True,
    'qubits_labels': {'Q1': 'q1', 'Q4': 'q4', 'Q5': 'q5'},
    'gate_group': [[0, 0, 2, 1], [1,2,3,2]],
    'measure_align': True,
    }
    c = Circuit(**dic)
    d = Drawer()
    d.plot(c)


def test_plot():
    plot_qasm(qasm=qasm)