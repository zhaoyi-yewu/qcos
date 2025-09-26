from qcos.cna.core.compiler import *
from qcos.cna.core.pulse import *
from qcos.cna.core import GlobalSetting
import unittest


class TestCompiler(unittest.TestCase):
    data = '''
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[6];
        creg c[6];
        gate test_single(theta, phi) a{
            rx(theta) a;
            h a;
            ry(-phi) a;
            rz(theta + phi) a;
            x a;
            y a;
            z a;
            s a;
            sdg a;
            tdg a;
            t a;
        }

        gate test_two(x, y) a, b{
            test_single(x, y) a;
            cx a, b;
            cy a, b;
            cz a, b;
            ch a, b;
            crx(x) a, b;
            cry(y) a, b;
            crz(x+y) a, b;
        }

        test_two(sin(1.2), 1.3) q[2], q[3];
        ccx q[0], q[1], q[4];
        barrier q;
        measure q[1] -> c[1];
    '''

    data1 = '''
          OPENQASM 2.0;
          include "qelib1.inc";
          qreg q[1];
          creg c[1];
          h q[0];
          h q[0];
          x q[0];
          rx(1) q[0];
          measure q->c;
      '''

    def test_parser(self):

        abs_tree = get_abs_tree(self.data)
        assert abs_tree != None
        assert abs_tree.type == 'top'

    def test_ir(self):

        abs_tree = get_abs_tree(self.data)
        qnum, ir = get_ir(abs_tree)
        assert qnum == 6
        for gate in ir:
            assert isinstance(gate, Gate)

    def test_transpile(self):
        abs_tree = get_abs_tree(self.data)
        _, ir = get_ir(abs_tree)
        transpiled_gates = transpiler(ir)
        for gate in transpiled_gates:
            assert gate.name in ['rx', 'ry', 'rz', 'cx', 'sync', 'measure']

    def test_optimizer(self):
        abs_tree = get_abs_tree(self.data1)
        _, ir = get_ir(abs_tree)
        assert len(ir) == 5
        opt_ir = optimizer(ir)
        assert len(opt_ir) == 3
        transpiled_gates = transpiler(opt_ir)
        opt_ir = optimizer(transpiled_gates)
        assert len(opt_ir) == 2

    def test_compile(self):
        qnum, seqs, meas = compile(self.data)
        assert qnum == 6
        for seq in seqs:
            assert isinstance(seq, (BasePulse, tuple))

    def test_decompose_rule(self):
        data = '''
            OPENQASM 2.0;
            include "qelib1.inc";

            qreg q[2];
            creg c[2];

            u3(0.1, 0.2, 0.3) q[0];
            h q[1];
            measure q->c;
        '''
        user_define = {
            'u3': {
                'params': ['a', 'b', 'c'],
                'gates': [
                    ('rz', [0], ["c"]),
                    ('rx', [0], ["pi/2"]),
                    ('rz', [0], ["b+pi"]),
                    ('rx', [0], ["pi/2"]),
                    ('rz', [0], ["a+pi"]),
                ]
            },
            'h': {
                'gates': [
                    ('ry', [0], ['pi/2'])
                ]
            }
        }

        GlobalSetting.set_decomposition_rule(user_define)
        ab = get_abs_tree(data)
        qnum, ir = get_ir(ab)
        gates = transpiler(ir)
        assert gates[0].name == 'rz' and gates[0].arg_value[0] == 0.3
        assert gates[1].name == 'rx' and gates[1].arg_value[0] == np.pi / 2
        assert gates[2].name == 'rz' and gates[2].arg_value[0] == 0.2 + np.pi
        assert gates[3].name == 'rx' and gates[3].arg_value[0] == np.pi / 2
        assert gates[4].name == 'rz' and gates[4].arg_value[0] == 0.1 + np.pi
        assert gates[5].name == 'ry' and gates[5].arg_value[0] == np.pi / 2

    def test_error(self):
        data = '''
            OPENQASM 2.0;
            includ "qelib1.inc"; 
            qreg q[2];
            creg c[2];
            x q[1];
        '''
        try:
            qnum, seqs, meas = compile(data)
        except SyntaxError as e:
            assert e.msg == "in line 3, can not parser the sentence at token: 'includ'"

        data = '''
            OPENQASM 2.0;
            include "qelib1.inc"; 
            qreg q[2];
            creg c[2];
            x q[1];
            test q[0];
        '''
        try:
            qnum, seqs, meas = compile(data)
        except NameError as e:
            assert e.args[0] == "in line 7, gate test is not defined"

    def test_for_empty(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            for int i in 5 {
            }
        '''
        compile(data)

    def test_for_gates(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            qreg q[2];
            creg c[2];
            for int i in 2 {
                x q[1];
                h q[0];
            }
        '''
        qnum, seqs, meas = compile(data)
        assert qnum == 2

    def test_for_gates_idx(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            qreg q[2];
            creg c[2];
            for int i in 2 {
                h q[i];
                x q[i];
            }
        '''
        qnum0, seqs0, meas0 = compile(data)
        assert qnum0 == 2

        data2 = '''
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[2];
            creg c[2];
            h q[0];
            x q[0];
            h q[1];
            x q[1];
        '''
        qnum1, seqs1, meas1 = compile(data2)
        assert str(seqs0) == str(seqs1)

    def test_int(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            int a = 1;
            int[16] b = 2;
            int c = a + 1;
            int d = c + b;
        '''
        compile(data)

    def test_bracket_reg(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            int i = 0;
            qreg q[2];
            creg c[2];
            h q[i];
            h q[i+1];
        '''
        qnum0, seqs0, meas0 = compile(data)
        assert qnum0 == 2

        data2 = '''
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[2];
            creg c[2];
            h q[0];
            h q[1];
        '''
        qnum1, seqs1, meas1 = compile(data2)
        assert str(seqs0) == str(seqs1)

    def test_acc(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            int a = 0;
            int b = 1;
            int c = b + b;
            int d = b * b;
            int e = d / a;
        '''
        try:
            qnum, seqs, meas = compile(data)
        except ZeroDivisionError as e:
            assert e.args[0] == "in line 8, divide by zero error"

    def test_for2_empty(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            qreg q[5];
            creg c[5];
            for int m in [:2] {
            }
            for int z in [0:5] {
            }

        '''
        qnum, seqs, meas = compile(data)

    def test_for2(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            qreg q[5];
            creg c[5];
            int[16] j = 3;
            for int m in [0:j] {
                x q[m];
            }
            for int z in [0:2:5] {
                h q[z];
            }
         
        '''
        qnum, seqs, meas = compile(data)

        data1 = '''
             OPENQASM 2.0;
             include "qelib1.inc";
             qreg q[5];
             creg c[5];
             x q[0];
             x q[1];
             x q[2];
             h q[0];
             h q[2];
             h q[4];
         '''
        qnum1, seqs1, meas1 = compile(data1)
        assert qnum1 == qnum
        assert str(seqs1) == str(seqs)
        assert meas1 == meas

    def test_array(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            array[int, 6] arr = {1, 2, 3, 5, 7, 11};
            arr[0] = 2;
        '''
        compile(data)

    def test_for_array(self):
        data = '''
             OPENQASM 3.0;
             include "stdgates.inc";
             qreg q[5];
             creg c[5];
             array[int[32], 2] arr = {1, 3};
             for int i in arr {
                h q[i];
             }
             '''
        qnum, seqs, meas = compile(data)

        data1 = '''
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[5];
            creg c[5];
            h q[1];
            h q[3];
        '''
        qnum1, seqs1, meas1 = compile(data1)
        assert str(seqs) == str(seqs1)

    def test_for_id(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            int a = 2;
            for int b in a {
            }
            array[int, 2] arr = {1, 2};
            for int b in arr {
            }
        '''
        qnum, seqs, meas = compile(data)

        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            float a = 2;
            for int b in a {
            }
        '''
        try:
            compile(data)
        except TypeError as e:
            assert e.args[0] == 'in line 5, var b and var a should both be int type'

        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            array[bool, 2] a = {true, false};
            for int b in a {
            }
        '''
        try:
            compile(data)
        except TypeError as e:
            assert e.args[0] == 'in line 5, var b and var a should both be int type'

    def test_array_error(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            array[int, 2] arr = {1, 2, 3};
        '''
        try:
            compile(data)
        except SyntaxError as e:
            assert e.args[0] == 'length in arrayType: 2 should be equal to the length in arrayLiteral: 3'

        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            array[int, 3.0] arr = {1, 2, 3};
        '''
        try:
            compile(data)
        except TypeError as e:
            assert e.args[0] == 'array length should be int'

        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            arr[0] = 1;
        '''
        try:
            compile(data)
        except NameError as e:
            assert e.args[0] == 'in line 4, variable a is not declared'

        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            int a = 1;
            a[0] = 2;
        '''
        try:
            compile(data)
        except TypeError as e:
            assert e.args[0] == 'in line 5, var a is not array'

        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            float a = 1.1;
            array[int, 2] arr = {1, 2};
            arr[a] = 1;
        '''
        try:
            compile(data)
        except TypeError as e:
            assert e.args[0] == 'in line 6, array index 1.1 is not int'

        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            array[int, 2] arr = {1, 2};
            arr[3] = 1;
        '''
        try:
            compile(data)
        except IndexError as e:
            assert e.args[0] == 'in line 5, array index 3 is out of bound'

    def test_var_not_defined(self):
        data = '''
            OPENQASM 3.0;
            include "stdgates.inc";
            int b;
            int a = b;
        '''
        try:
            compile(data)
        except NameError as e:
            assert e.args[0] == 'in line 5, variable b is only declared but not defined'

    def test_bit_qubit(self):
        data_error = '''
                    OPENQASM 2.0;
                    include "qelib1.inc";
                    bit[20] b_multi;
                    bit b_single;
                    qubit[10] q_multi;
                    qubit q_single;
                '''
        data_correct = '''
                    OPENQASM 3.0;
                    include "stdgates.inc";
                    bit[20] b_multi;
                    bit b_single;
                    qubit[9] q_multi;
                    qubit q_single;
                '''
        # 测试版本错误场景
        try:
            compile(data_error)
        except TypeError as e:
            e.args = "in line 1: version error"
        # 测试正确定义bit及qubit类型场景
        q_num, _, _ = compile(data_correct)
        assert q_num == 10

    def test_float(self):
        data_error = '''
                    OPENQASM 3.0;
                    include "stdgates.inc";
                    float a;
                    float b = 1.0;
                    float c = a + b;
                '''
        data_correct = '''
                    OPENQASM 3.0;
                    include "stdgates.inc";
                    int a = 1.2;
                    float b = 2.0;
                    float c = a + b;
                    qubit[2] q;
                    for float i in 2 {
                        y q[0];
                        x q[1];
                    }
                '''
        # 测试变量未定义错误场景
        try:
            compile(data_error)
        except NameError as e:
            assert e.args[0] == "in line 6, variable a is only declared but not defined"
        # 测试正确场景
        q_num, seqs, meas = compile(data_correct)
        assert len(seqs) == 4

    def test_bool(self):
        bool_data = '''
                    OPENQASM 3.0;
                    include "stdgates.inc";
                    bool a = true;
                    bool b = false;
                '''
        # 测试支持bool类型
        q_num, seqs, meas = compile(bool_data)

    def test_assignment(self):
        data_error = '''
                    OPENQASM 3.0;
                    include "stdgates.inc";
                    int b = 1;
                    a = b;
                    c = 1;
                '''
        data_correct = '''
                    OPENQASM 3.0;
                    include "stdgates.inc";
                    int a;
                    int b;
                    bool c;
                    b = 1;
                    a = 2;
                    b = a;
                    c = true;
                '''
        # 测试变量未定义错误场景
        try:
            compile(data_error)
        except NameError as e:
            assert e.args[0] == "in line 5, variable a is not declared"
        # 测试正确场景
        q_num, seqs, meas = compile(data_correct)

    def test_var_name(self):
        # 测试变量名重复报错
        data = '''
                OPENQASM 3.0;
                include "stdgates.inc";
                qubit[5]  q;
                int q = 1;
                '''
        try:
            compile(data)
        except NameError as e:
            assert e.args[0] == "in line 5, var q is existed"


if __name__ == '__main__':
    # 运行单元测试
    unittest.main()
