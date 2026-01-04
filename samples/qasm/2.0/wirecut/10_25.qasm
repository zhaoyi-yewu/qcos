OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];

h q[0];
t q[1];
cx q[0], q[1];
rz(1.2) q[1];
cx q[1], q[2];
x q[2];

h q[3];
x q[4];
cx q[3], q[4];
rz(0.7) q[4];
cx q[4], q[5];
t q[5];

x q[6];
h q[6];
rz(0.3) q[7];
cx q[6], q[7];
cx q[7], q[8];
t q[8];

cx q[2], q[5];
cx q[1], q[4];
cx q[4], q[7];
cx q[5], q[9];

rz(0.5) q[9];
x q[9];
h q[9];

measure q -> c;
