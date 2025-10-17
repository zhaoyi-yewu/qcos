OPENQASM 3.0;
include "stdgates.inc";
qubit[100] q;
bit[100] c;
for int m in [0:49999] {
    rx(1) q;
}
measure q -> c;
