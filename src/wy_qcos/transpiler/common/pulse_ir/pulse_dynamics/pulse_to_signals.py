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
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Pulse schedule to Signals converter."""

from collections.abc import Callable
import functools
import math
from warnings import warn

import numpy as np
import sympy as sym

from wy_qcos.transpiler.common.pulse_ir.pulse import (
    Schedule,
    Play,
    ShiftPhase,
    SetPhase,
    ShiftFrequency,
    SetFrequency,
    Waveform,
    MeasureChannel,
    DriveChannel,
    ControlChannel,
    AcquireChannel,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.pulse.library import SymbolicPulse
from wy_qcos.transpiler.common.pulse_ir.compatible.exceptions import (
    QiskitError,
)

from qiskit_dynamics import DYNAMICS_NUMPY as unp
from qiskit_dynamics import ArrayLike

from qiskit_dynamics.signals import DiscreteSignal

try:
    import jax
    import jax.numpy as jnp
except ImportError:
    pass


class InstructionToSignals:
    """Converts pulse instructions to signals to be used in models.

    The :class:`InstructionsToSignals` class converts a pulse schedule to
    a list of signals that can be given to a model. This conversion is
    done by calling the :meth:`get_signals` method on a schedule. The
    converter applies to instances of
    :class:`~wy_qcos.transpiler.common.pulse_ir.pulse.Schedule`.
    Instances of
    :class:`~wy_qcos.transpiler.common.pulse_ir.pulse.ScheduleBlock`
    must first be converted to
    :class:`~wy_qcos.transpiler.common.pulse_ir.pulse.Schedule` using
    the
    :func:`~wy_qcos.transpiler.common.pulse_ir.pulse.transforms.block_to_schedule`
    function in Qiskit Pulse.

    The converter can be initialized with the optional arguments
    ``carriers`` and ``channels``. When ``channels`` is given, only the
    signals specified by name in ``channels`` are returned. The
    ``carriers`` dictionary specifies the analog carrier frequency of
    each channel. Here, the keys are the channel name, e.g. ``d12`` for
    drive channel number ``12``, and the values are the corresponding
    frequency. If a channel is not present in ``carriers`` it is assumed
    that the analog carrier frequency is zero.

    See the :meth:`get_signals` method documentation for a detailed
    description of how pulse schedules are interpreted and translated
    into :class:`.DiscreteSignal` objects.
    """

    def __init__(
        self,
        dt: float,
        carriers: dict[str, float] | None = None,
        channels: list[str] | None = None,
    ):
        """Initialize pulse schedule to signals converter.

        Args:
            dt: Length of the samples. This is required because pulse
                schedules are specified in units of ``dt`` and typically
                do not carry the value with them.
            carriers: A dict of analog carrier frequencies. The keys are
                the names of the channels
                and the values are the corresponding carrier frequency.
            channels: A list of channels that the :meth:`get_signals`
                method should return. This causes
                :meth:`get_signals` to return signals in the same order
                as ``channels``. Channels present in the schedule but
                absent from ``channels`` are excluded. If ``None`` is
                given, all channels present in the pulse schedule are
                returned.
        """
        self._dt = dt
        self._channels = channels
        self._carriers = carriers or {}

    def get_signals(self, schedule: Schedule) -> list[DiscreteSignal]:
        r"""Convert a schedule to corresponding discrete signals.

        Which channels are converted, and the order they are returned,
        is controlled by the ``channels`` argument at instantiation.
        The ``carriers`` argument sets the analog carrier frequency for
        each channel, which is fixed for the full duration. For a given
        channel, the :math:`k^{th}` envelope sample for the
        corresponding :class:`.DiscreteSignal` is determined according
        to the following formula:

        .. math::
            f(k) \exp(i(2\pi \Delta\nu(k) k dt + \phi(k) + 2 \pi \phi_a(k))),

        where:

        * :math:`f(k)` is the waveform value at the :math:`k^{th}` time
          step specified by ``Play`` instructions.
        * :math:`\Delta\nu(k)` is the frequency deviation from the
          analog carrier at time step :math:`k`.
        * :math:`dt` is the sample rate specified by the ``dt``
          instantiation argument.
        * :math:`\phi(k)` is the channel phase at time step :math:`k`.
        * :math:`\phi_a(k)` is the phase correction term at time step
          :math:`k`.

        The schedule is processed in temporal order. ``Play`` appends
        samples using the current values of :math:`\Delta\nu`,
        :math:`\phi`, and :math:`\phi_a`, all initialized to
        :math:`0`. ``ShiftPhase`` and ``SetPhase`` update
        :math:`\phi`. ``ShiftFrequency`` and ``SetFrequency`` update
        :math:`\Delta\nu` and :math:`\phi_a` to preserve carrier-wave
        continuity.

        If, at any sample point :math:`k`, :math:`\Delta\nu(k)` is
        larger than the Nyquist sampling rate given by ``dt``, a
        warning is raised.

        Args:
            schedule: The schedule to represent in terms of signals.
                Instances of
                :class:`~wy_qcos.transpiler.common.pulse_ir.pulse.ScheduleBlock`
                must first be converted to
                :class:`~wy_qcos.transpiler.common.pulse_ir.pulse.Schedule`
                using the pulse ``block_to_schedule`` transform.

        Returns:
            A list of :class:`.DiscreteSignal` instances.
        """
        signals: dict[str, DiscreteSignal] = {}
        phases: dict[str, float] = {}
        frequency_shifts: dict[str, float] = {}
        phase_accumulations: dict[str, float] = {}

        if self._channels is not None:
            schedule = schedule.filter(
                channels=[self._get_channel(ch) for ch in self._channels]
            )

        for channel in schedule.channels:
            phases[channel.name] = 0.0
            frequency_shifts[channel.name] = 0.0
            phase_accumulations[channel.name] = 0.0

            carrier_freq = self._carriers.get(channel.name, 0.0)

            signals[channel.name] = DiscreteSignal(
                samples=[],
                dt=self._dt,
                name=channel.name,
                carrier_freq=carrier_freq,
            )

        for start_sample, inst in schedule.instructions:
            # get channel name if instruction has it
            chan_name = inst.channel.name if hasattr(inst, "channel") else None

            if chan_name is None:
                continue

            if isinstance(inst, Play):
                # get the instruction samples
                inst_samples = None
                if isinstance(inst.pulse, Waveform):
                    inst_samples = inst.pulse.samples
                else:
                    inst_samples = get_samples(inst.pulse)

                # build sample array to append to signal
                times = self._dt * (
                    start_sample + np.arange(len(inst_samples))
                )
                phase_argument = (
                    2.0 * math.pi * frequency_shifts[chan_name] * times
                    + phases[chan_name]
                    + 2.0 * math.pi * phase_accumulations[chan_name]
                )
                samples = inst_samples * unp.exp(1.0j * phase_argument)
                signals[chan_name].add_samples(start_sample, samples)

            if isinstance(inst, ShiftPhase):
                phases[chan_name] += inst.phase

            if isinstance(inst, SetPhase):
                phases[chan_name] = inst.phase

            if isinstance(inst, ShiftFrequency):
                frequency_shifts[chan_name] = (
                    frequency_shifts[chan_name] + inst.frequency
                )
                phase_accumulations[chan_name] = (
                    phase_accumulations[chan_name]
                    - inst.frequency * start_sample * self._dt
                )
                _nyquist_warn(frequency_shifts[chan_name], self._dt, chan_name)

            if isinstance(inst, SetFrequency):
                phase_accumulations[chan_name] = phase_accumulations[
                    chan_name
                ] - (
                    (
                        inst.frequency
                        - (
                            frequency_shifts[chan_name]
                            + signals[chan_name].carrier_freq
                        )
                    )
                    * start_sample
                    * self._dt
                )
                frequency_shifts[chan_name] = (
                    inst.frequency - signals[chan_name].carrier_freq
                )
                _nyquist_warn(frequency_shifts[chan_name], self._dt, chan_name)

        # ensure all signals have the same number of samples
        max_duration = 0
        for sig in signals.values():
            max_duration = max(max_duration, sig.duration)

        for sig in signals.values():
            if sig.duration < max_duration:
                sig.add_samples(
                    start_sample=sig.duration,
                    samples=np.zeros(
                        max_duration - sig.duration,
                        dtype=complex,
                    ),
                )

        # filter the channels
        if self._channels is None:
            return list(signals.values())

        return_signals = []
        for chan_name in self._channels:
            signal = signals.get(
                chan_name,
                DiscreteSignal(
                    samples=[],
                    dt=self._dt,
                    name=chan_name,
                    carrier_freq=0.0,
                ),
            )

            return_signals.append(signal)
        return return_signals

    @staticmethod
    def get_awg_signals(
        signals: list[DiscreteSignal], if_modulation: float
    ) -> list[DiscreteSignal]:
        r"""Create AWG I/Q signals for the supplied discrete signals.

        These signals correspond to the output ports of an arbitrary
        waveform generator used with IQ mixers. For each input signal,
        the output list contains I and Q components representing the
        real and imaginary parts, respectively, of

        .. math::
            \Omega(t) e^{i \omega_{if} t}

        where :math:`\Omega` is the complex-valued pulse envelope and
        :math:`\omega_{if}` is the intermediate frequency.

        Args:
            signals: A list of signals for which to create I and Q.
            if_modulation: The intermediate frequency with which the AWG
                modulates the pulse envelopes.

        Returns:
            A list of signals twice as long as the input. Each input
            signal produces one I signal and one Q signal.
        """
        new_signals = []

        for sig in signals:
            new_freq = sig.carrier_freq + if_modulation

            samples_i = sig.samples
            samples_q = unp.imag(samples_i) - 1.0j * unp.real(samples_i)

            sig_i = DiscreteSignal(
                sig.dt,
                samples_i,
                sig.start_time,
                new_freq,
                sig.phase,
                sig.name + "_i",
            )
            sig_q = DiscreteSignal(
                sig.dt,
                samples_q,
                sig.start_time,
                new_freq,
                sig.phase,
                sig.name + "_q",
            )

            new_signals += [sig_i, sig_q]

        return new_signals

    def _get_channel(self, channel_name: str):
        """Return the channel corresponding to the given name."""
        try:
            prefix = channel_name[0]
            index = int(channel_name[1:])

            if prefix == "d":
                return DriveChannel(index)

            if prefix == "m":
                return MeasureChannel(index)

            if prefix == "u":
                return ControlChannel(index)

            if prefix == "a":
                return AcquireChannel(index)

            raise QiskitError(
                "Unsupported channel name "
                f"{channel_name} in {self.__class__.__name__}"
            )

        except (KeyError, IndexError, ValueError) as error:
            raise QiskitError(
                "Invalid channel name "
                f"{channel_name} given to {self.__class__.__name__}."
            ) from error


def get_samples(pulse: SymbolicPulse) -> ArrayLike:
    """Return samples computed from the pulse formula and parameters.

    Args:
        pulse: SymbolicPulse class.

    Returns:
        Samples of the pulse.

    Raises:
        PulseError: When parameters are not assigned.
        PulseError: When expression for pulse envelope is not assigned.
        PulseError: When a free symbol value is not defined in the pulse
            instance parameters.
    """
    envelope = pulse.envelope
    pulse_params = pulse.parameters
    if pulse.is_parameterized():
        raise PulseError(
            "Unassigned parameter exists. All parameters must be assigned."
        )

    if envelope is None:
        raise PulseError("Pulse envelope expression is not assigned.")

    args = []
    try:
        backend = (
            "jax"
            if any(
                isinstance(v, jax.core.Tracer) for v in pulse_params.values()
            )
            else "numpy"
        )
    except (ImportError, NameError):
        backend = "numpy"
    for symbol in sorted(envelope.free_symbols, key=lambda s: s.name):
        if symbol.name == "t":
            times = unp.arange(0, pulse_params["duration"]) + 1 / 2
            args.insert(0, times)
            continue
        try:
            args.append(pulse_params[symbol.name])
        except KeyError as ex:
            raise PulseError(
                f"Pulse parameter '{symbol.name}' is not defined "
                "for this instance. "
                "Please check your waveform expression is correct."
            ) from ex
    return _lru_cache_expr(
        envelope,
        backend,
    )(*args)


@functools.cache
def _lru_cache_expr(expr: sym.Expr, backend) -> Callable:
    """A helper function to get lambdified expression.

    Args:
        expr: Symbolic expression to evaluate.
        backend: Array backend.

    Returns:
        lambdified expression.
    """
    params = []
    for param in sorted(expr.free_symbols, key=lambda s: s.name):
        if param.name == "t":
            params.insert(0, param)
            continue
        params.append(param)
    return sym.lambdify(params, expr, modules=backend)


def _nyquist_warn(frequency_shift: ArrayLike, dt: float, channel: str):
    """Raise a warning for frequency shifts above the Nyquist limit."""
    if (
        isinstance(frequency_shift, (int, float, list, np.ndarray))
        or not isinstance(jnp.array(0), jax.core.Tracer)
    ) and np.abs(frequency_shift) > 0.5 / dt:
        warn(
            "Due to SetFrequency and ShiftFrequency instructions, "
            "the digital carrier frequency "
            f"of channel {channel} is larger than the Nyquist frequency "
            "of the envelope sample size dt. As shifts of the frequency "
            "from the analog frequency are handled digitally, "
            "this will result in aliasing effects."
        )
