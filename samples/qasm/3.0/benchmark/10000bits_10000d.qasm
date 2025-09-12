OPENQASM 3.0;
include "stdgates.inc";
qreg q[10000];
creg c[10000];
for int m in [0:9999] {
    for int i in [0:9999] {
        rx(1) q[i];
    }
}
measure q -> c;
