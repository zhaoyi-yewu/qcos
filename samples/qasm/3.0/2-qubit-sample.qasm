OPENQASM 3.0;
include "stdgates.inc";
gate rzz(p0) _gate_q_0, _gate_q_1 {
  cx _gate_q_0, _gate_q_1;
  rz(p0) _gate_q_1;
  cx _gate_q_0, _gate_q_1;
}
bit[2] meas;
qubit[2] q;
ry(pi/2) q[0];
rx(pi) q[0];
ry(pi/2) q[1];
rx(pi) q[1];
rzz(pi/2) q[0], q[1];
rx(pi/2) q[0];
ry(pi/2) q[0];
rx(-pi/2) q[0];
ry(pi/2) q[1];
rx(pi/2) q[1];
barrier q[0], q[1];
meas[0] = measure q[0];
meas[1] = measure q[1];
