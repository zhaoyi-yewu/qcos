#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY
# OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Default pulse calibrations for a standard gate set.

All single-qubit gates use DRAG pulses on DriveChannel(q).
Virtual-Z decomposition is used for phase gates (rz, p, u1, s, t, z, etc.).
Two-qubit gates (cx, cz, swap) use GaussianSquare cross-resonance pulses.

Gate decompositions follow standard textbook identities:
  - H  = U2(0, π)        = RZ(π) · SX · RZ(0)  (phase + √X + phase)
  - X  = two SX pulses
  - Y  = RZ(π) · X
  - Z  = RZ(π)           (virtual)
  - S  = RZ(π/2)         (virtual)
  - Sdg= RZ(-π/2)        (virtual)
  - T  = RZ(π/4)         (virtual)
  - Tdg= RZ(-π/4)        (virtual)
  - SX = DRAG pulse
  - SXdg = SX with angle=π (conjugate)
  - RX(θ) = RZ(-π/2)·SX·RZ(π-θ)·SX·RZ(-π/2)  (Euler decomp)
  - RY(θ) = SX·RZ(π-θ)·SX·RZ(π)               (Euler decomp)
  - RZ(θ) = shift_phase   (virtual)
  - P(λ)  = RZ(λ)         (virtual, same as rz up to global phase)
  - U1(λ) = RZ(λ)
  - U2(φ,λ) = RZ(λ+π/2)·SX·RZ(φ-π/2)
  - U3(θ,φ,λ) = RZ(λ)·SX·RZ(θ+π)·SX·RZ(φ+π)
  - U(θ,φ,λ) = U3(θ,φ,λ)
  - CX = cross-resonance
  - CZ = RZ(-π/2) on target · CX · RZ(-π/2) on target (+ Hadamards)
  - SWAP = CX · CX(reversed) · CX
"""

import numpy as np

import wy_qcos.transpiler.common.pulse_ir.pulse as pulse
from wy_qcos.transpiler.common.pulse_ir.pulse import InstructionScheduleMap


def _build_sx(
    duration: int, amp: float, sigma: float, beta: float, qubit: int
):
    """SX gate: π/2 rotation around X via DRAG pulse."""
    with pulse.build(name="sx") as sched:
        pulse.play(
            pulse.Drag(duration=duration, amp=amp, sigma=sigma, beta=beta),
            pulse.DriveChannel(qubit),
        )
    return sched


def _build_sxdg(
    duration: int, amp: float, sigma: float, beta: float, qubit: int
):
    """SXdg gate: -π/2 rotation around X (conjugate of SX)."""
    with pulse.build(name="sxdg") as sched:
        pulse.play(
            pulse.Drag(
                duration=duration, amp=amp, sigma=sigma, beta=beta, angle=np.pi
            ),
            pulse.DriveChannel(qubit),
        )
    return sched


def _build_x(duration: int, amp: float, sigma: float, beta: float, qubit: int):
    """X gate: two SX pulses."""
    with pulse.build(name="x") as sched:
        pulse.play(
            pulse.Drag(duration=duration, amp=amp, sigma=sigma, beta=beta),
            pulse.DriveChannel(qubit),
        )
        pulse.play(
            pulse.Drag(duration=duration, amp=amp, sigma=sigma, beta=beta),
            pulse.DriveChannel(qubit),
        )
    return sched


def _build_cx(
    duration_2q: int,
    amp_cx_drive: float,
    amp_cx_target: float,
    amp_cr: float,
    sigma_2q: float,
    width_2q: float,
    control: int,
    target: int,
):
    """CX gate via cross-resonance."""
    with pulse.build(name="cx") as sched:
        pulse.play(
            pulse.GaussianSquare(
                duration=duration_2q,
                amp=amp_cx_drive,
                sigma=sigma_2q,
                width=width_2q,
            ),
            pulse.DriveChannel(control),
        )
        pulse.play(
            pulse.GaussianSquare(
                duration=duration_2q,
                amp=amp_cx_target,
                sigma=sigma_2q,
                width=width_2q,
            ),
            pulse.DriveChannel(target),
        )
        pulse.play(
            pulse.GaussianSquare(
                duration=duration_2q,
                amp=amp_cr,
                sigma=sigma_2q,
                width=width_2q,
            ),
            pulse.ControlChannel(control),
        )
    return sched


def build_default_inst_map(
    num_qubits: int = 2,
    dt: float = 1 / 4.5,
    duration_1q: int = 160,
    duration_2q: int = 640,
    amp_sx: float = 0.5,
    sigma_1q: float | None = None,
    beta: float = 2.0,
    amp_cx_drive: float = 0.3,
    amp_cx_target: float = 0.2,
    amp_cr: float = 0.4,
    sigma_2q: float | None = None,
    width_2q: float | None = None,
) -> InstructionScheduleMap:
    """Build a default instruction schedule map.

    The map contains pulse calibrations for a standard gate set.

    Args:
        num_qubits: Number of qubits to calibrate.
        dt: Sample time step (ns).
        duration_1q: Duration of single-qubit DRAG pulses (in dt units).
        duration_2q: Duration of two-qubit CR pulses (in dt units).
        amp_sx: Amplitude of the SX DRAG pulse.
        sigma_1q: Gaussian sigma for 1Q pulses. Defaults to duration_1q / 4.
        beta: DRAG correction parameter.
        amp_cx_drive: CX drive amplitude on control qubit.
        amp_cx_target: CX drive amplitude on target qubit.
        amp_cr: Cross-resonance amplitude.
        sigma_2q: Gaussian sigma for 2Q pulses. Defaults to duration_2q / 8.
        width_2q: Flat-top width for 2Q GaussianSquare. Defaults to
            duration_2q - 4 * sigma_2q.

    Returns:
        InstructionScheduleMap with calibrations for: sx, sxdg, x, y, z, h,
        s, sdg, t, tdg, rx, ry, rz, p, u1, u2, u3, u, cx, cz, swap.
    """
    if sigma_1q is None:
        sigma_1q = duration_1q / 4.0
    if sigma_2q is None:
        sigma_2q = duration_2q / 8.0
    if width_2q is None:
        width_2q = duration_2q - 4 * sigma_2q

    inst_map = InstructionScheduleMap()

    for q in range(num_qubits):
        # ---- SX ----
        sx_sched = _build_sx(duration_1q, amp_sx, sigma_1q, beta, q)
        inst_map.add("sx", qubits=q, schedule=sx_sched)

        # ---- SXdg ----
        sxdg_sched = _build_sxdg(duration_1q, amp_sx, sigma_1q, beta, q)
        inst_map.add("sxdg", qubits=q, schedule=sxdg_sched)

        # ---- X ----
        x_sched = _build_x(duration_1q, amp_sx, sigma_1q, beta, q)
        inst_map.add("x", qubits=q, schedule=x_sched)

        # ---- RZ (virtual Z) ----
        def _rz(angle, _q=q):
            with pulse.build(name="rz") as rz_sched:
                pulse.shift_phase(-float(angle), pulse.DriveChannel(_q))
            return rz_sched

        inst_map.add("rz", qubits=q, schedule=_rz, arguments=["angle"])

        # ---- P (phase gate, same as rz up to global phase) ----
        def _p(lam, _q=q):
            with pulse.build(name="p") as p_sched:
                pulse.shift_phase(-float(lam), pulse.DriveChannel(_q))
            return p_sched

        inst_map.add("p", qubits=q, schedule=_p, arguments=["lam"])

        # ---- U1(λ) = RZ(λ) ----
        def _u1(lam, _q=q):
            with pulse.build(name="u1") as u1_sched:
                pulse.shift_phase(-float(lam), pulse.DriveChannel(_q))
            return u1_sched

        inst_map.add("u1", qubits=q, schedule=_u1, arguments=["lam"])

        # ---- Z = RZ(π) ----
        with pulse.build(name="z") as z_sched:
            pulse.shift_phase(-np.pi, pulse.DriveChannel(q))
        inst_map.add("z", qubits=q, schedule=z_sched)

        # ---- S = RZ(π/2) ----
        with pulse.build(name="s") as s_sched:
            pulse.shift_phase(-np.pi / 2, pulse.DriveChannel(q))
        inst_map.add("s", qubits=q, schedule=s_sched)

        # ---- Sdg = RZ(-π/2) ----
        with pulse.build(name="sdg") as sdg_sched:
            pulse.shift_phase(np.pi / 2, pulse.DriveChannel(q))
        inst_map.add("sdg", qubits=q, schedule=sdg_sched)

        # ---- T = RZ(π/4) ----
        with pulse.build(name="t") as t_sched:
            pulse.shift_phase(-np.pi / 4, pulse.DriveChannel(q))
        inst_map.add("t", qubits=q, schedule=t_sched)

        # ---- Tdg = RZ(-π/4) ----
        with pulse.build(name="tdg") as tdg_sched:
            pulse.shift_phase(np.pi / 4, pulse.DriveChannel(q))
        inst_map.add("tdg", qubits=q, schedule=tdg_sched)

        # ---- Y = RZ(π) · X ----
        with pulse.build(name="y") as y_sched:
            pulse.shift_phase(-np.pi, pulse.DriveChannel(q))
            pulse.play(
                pulse.Drag(
                    duration=duration_1q, amp=amp_sx, sigma=sigma_1q, beta=beta
                ),
                pulse.DriveChannel(q),
            )
            pulse.play(
                pulse.Drag(
                    duration=duration_1q, amp=amp_sx, sigma=sigma_1q, beta=beta
                ),
                pulse.DriveChannel(q),
            )
        inst_map.add("y", qubits=q, schedule=y_sched)

        # ---- H = U2(0, π) = RZ(π + π/2)·SX·RZ(0 - π/2) ----
        with pulse.build(name="h") as h_sched:
            pulse.shift_phase(
                np.pi / 2, pulse.DriveChannel(q)
            )  # RZ(-π/2) -> phase +π/2
            pulse.play(
                pulse.Drag(
                    duration=duration_1q, amp=amp_sx, sigma=sigma_1q, beta=beta
                ),
                pulse.DriveChannel(q),
            )
            pulse.shift_phase(
                -np.pi / 2 - np.pi, pulse.DriveChannel(q)
            )  # RZ(3π/2)
        inst_map.add("h", qubits=q, schedule=h_sched)

        # ---- RX(θ) = RZ(-π/2)·SX·RZ(π-θ)·SX·RZ(-π/2) ----
        def _rx(theta, _q=q):
            with pulse.build(name="rx") as rx_sched:
                pulse.shift_phase(
                    np.pi / 2, pulse.DriveChannel(_q)
                )  # RZ(-π/2)
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(
                    -(np.pi - float(theta)), pulse.DriveChannel(_q)
                )  # RZ(π-θ)
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(
                    np.pi / 2, pulse.DriveChannel(_q)
                )  # RZ(-π/2)
            return rx_sched

        inst_map.add("rx", qubits=q, schedule=_rx, arguments=["theta"])

        # ---- RY(θ) = SX·RZ(π-θ)·SX·RZ(π) ----
        def _ry(theta, _q=q):
            with pulse.build(name="ry") as ry_sched:
                pulse.shift_phase(-np.pi, pulse.DriveChannel(_q))  # RZ(π)
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(
                    -(np.pi - float(theta)), pulse.DriveChannel(_q)
                )  # RZ(π-θ)
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
            return ry_sched

        inst_map.add("ry", qubits=q, schedule=_ry, arguments=["theta"])

        # ---- U2(φ, λ) = RZ(λ+π/2)·SX·RZ(φ-π/2) ----
        def _u2(phi, lam, _q=q):
            with pulse.build(name="u2") as u2_sched:
                pulse.shift_phase(
                    -(float(phi) - np.pi / 2), pulse.DriveChannel(_q)
                )
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(
                    -(float(lam) + np.pi / 2), pulse.DriveChannel(_q)
                )
            return u2_sched

        inst_map.add("u2", qubits=q, schedule=_u2, arguments=["phi", "lam"])

        # ---- U3(θ, φ, λ) = RZ(λ)·SX·RZ(θ+π)·SX·RZ(φ+π) ----
        def _u3(theta, phi, lam, _q=q):
            with pulse.build(name="u3") as u3_sched:
                pulse.shift_phase(
                    -(float(phi) + np.pi), pulse.DriveChannel(_q)
                )
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(
                    -(float(theta) + np.pi), pulse.DriveChannel(_q)
                )
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(-float(lam), pulse.DriveChannel(_q))
            return u3_sched

        inst_map.add(
            "u3", qubits=q, schedule=_u3, arguments=["theta", "phi", "lam"]
        )

        # ---- U(θ, φ, λ) = U3(θ, φ, λ) ----
        def _u(theta, phi, lam, _q=q):
            with pulse.build(name="u") as u_sched:
                pulse.shift_phase(
                    -(float(phi) + np.pi), pulse.DriveChannel(_q)
                )
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(
                    -(float(theta) + np.pi), pulse.DriveChannel(_q)
                )
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(_q),
                )
                pulse.shift_phase(-float(lam), pulse.DriveChannel(_q))
            return u_sched

        inst_map.add(
            "u", qubits=q, schedule=_u, arguments=["theta", "phi", "lam"]
        )

    # ---- Two-qubit gates ----
    for ctrl in range(num_qubits):
        for tgt in range(num_qubits):
            if ctrl == tgt:
                continue

            # ---- CX ----
            cx_sched = _build_cx(
                duration_2q,
                amp_cx_drive,
                amp_cx_target,
                amp_cr,
                sigma_2q,
                width_2q,
                ctrl,
                tgt,
            )
            inst_map.add("cx", qubits=(ctrl, tgt), schedule=cx_sched)

            # ---- CZ = H(target)·CX·H(target) ----
            # RZ(-π/2)·SX·RZ(-3π/2)·CX·RZ(π/2)·SX·RZ(-π/2)
            with pulse.build(name="cz") as cz_sched:
                # H on target
                pulse.shift_phase(np.pi / 2, pulse.DriveChannel(tgt))
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(tgt),
                )
                pulse.shift_phase(-np.pi / 2 - np.pi, pulse.DriveChannel(tgt))
                # CX
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_drive,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(ctrl),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_target,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(tgt),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cr,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.ControlChannel(ctrl),
                )
                # H on target
                pulse.shift_phase(np.pi / 2, pulse.DriveChannel(tgt))
                pulse.play(
                    pulse.Drag(
                        duration=duration_1q,
                        amp=amp_sx,
                        sigma=sigma_1q,
                        beta=beta,
                    ),
                    pulse.DriveChannel(tgt),
                )
                pulse.shift_phase(-np.pi / 2 - np.pi, pulse.DriveChannel(tgt))
            inst_map.add("cz", qubits=(ctrl, tgt), schedule=cz_sched)

            # ---- SWAP = CX(c,t)·CX(t,c)·CX(c,t) ----
            with pulse.build(name="swap") as swap_sched:
                # First CX(ctrl, tgt)
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_drive,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(ctrl),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_target,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(tgt),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cr,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.ControlChannel(ctrl),
                )
                # Second CX(tgt, ctrl)
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_drive,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(tgt),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_target,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(ctrl),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cr,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.ControlChannel(tgt),
                )
                # Third CX(ctrl, tgt)
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_drive,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(ctrl),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cx_target,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.DriveChannel(tgt),
                )
                pulse.play(
                    pulse.GaussianSquare(
                        duration=duration_2q,
                        amp=amp_cr,
                        sigma=sigma_2q,
                        width=width_2q,
                    ),
                    pulse.ControlChannel(ctrl),
                )
            inst_map.add("swap", qubits=(ctrl, tgt), schedule=swap_sched)

    return inst_map
