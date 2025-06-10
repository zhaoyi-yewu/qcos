from qcos.cna import *
import os

class TestRea():
    
    def test_py_rea(self):
        
        row = 10
        column = 20

        target = []
        for i in range(3, 6):
            for j in range(9, 11):
                target += [i, j]

        pyrea_ins = PyRea('test/na_file.json')
        pyrea_ins.target = target

        for i in range(1):
            atom = np.random.randint(0,2,row*column)
            pyrea_ins.transport(atom)
            sim_res, mov_cnt, grab_cnt = pyrea_ins.mov_simulate(atom, pyrea_ins.output)
            for i in range(3, 6):
                for j in range(9, 11):
                    assert sim_res[i,j] == 1