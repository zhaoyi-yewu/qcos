OPENQASM 3.0;
include "stdgates.inc";
qreg q[100];
creg c[100];
for int m in [0:49999] {
    for int i in [0:99] {
        rx(1) q[i];
    }
}
measure q -> c;
