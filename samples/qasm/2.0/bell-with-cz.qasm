OPENQASM 2.0;
include "qelib1.inc";

qreg q[2];
creg c[2];

// Bell state via H + CNOT, where the CNOT is decomposed using a CZ
// gate (CNOT = (I⊗H) · CZ · (I⊗H)). The CZ gate lets ZNE exercise its
// CZ-folding noise scaling on a genuine Bell-pair circuit.
h q[0];
h q[1];
cz q[0],q[1];
h q[1];

measure q -> c;
