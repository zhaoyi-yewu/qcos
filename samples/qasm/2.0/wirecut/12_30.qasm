OPENQASM 2.0;
include "qelib1.inc";

qreg q[12];
creg c[12];

h q[0];
cx q[0],q[1];
t q[1];
cx q[1],q[2];
x q[2];
cx q[2],q[4];
t q[4];
cx q[4],q[6];
z q[6];
cx q[6],q[8];
h q[8];
cx q[7],q[8];
x q[7];
cx q[7],q[9];
t q[9];
cx q[10],q[11];
z q[11];

h q[3];
cx q[3],q[1];
t q[3];
x q[5];
cx q[5],q[3];
z q[5];

h q[10];
cx q[10],q[8];
t q[10];
x q[10];

h q[11];
cx q[11],q[6];
x q[11];

measure q -> c;
