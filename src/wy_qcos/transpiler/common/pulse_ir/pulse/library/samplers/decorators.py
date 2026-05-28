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
"""Decorator helpers for sampling continuous pulse functions.

This module adapts continuous pulse callables of the form
``f(times: np.ndarray, *args, **kwargs) -> np.ndarray`` into sampled pulse
callables that accept ``duration`` and return discrete waveforms.

The implementation is intentionally more verbose than a plain
``functools.wraps``-based decorator because a sampler needs to preserve the
public signature and documentation of the sampled function, not the internal
helper that performs the discretization.

To do this, the generated wrappers update annotations and docstrings after
decoration and avoid exposing the wrong wrapped signature through
``__wrapped__``. This keeps standard samplers such as ``left``, ``right``,
and ``midpoint`` inspectable, while still allowing users to build custom
samplers when needed.
"""

from __future__ import annotations
import functools
import textwrap
import pydoc
from collections.abc import Callable

import numpy as np

from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.pulse.library.waveform import Waveform
from wy_qcos.transpiler.common.pulse_ir.pulse.library.samplers import (
    strategies,
)


def functional_pulse(func: Callable) -> Callable:
    """A decorator for generating Waveform from python callable.

    Args:
        func: A function describing pulse envelope.

    Raises:
        PulseError: when invalid function is specified.
    """

    @functools.wraps(func)
    def to_pulse(duration, *args, name=None, **kwargs):
        """Return Waveform."""
        if isinstance(duration, (int, np.integer)) and duration > 0:
            samples = func(duration, *args, **kwargs)
            samples = np.asarray(samples, dtype=np.complex128)
            return Waveform(samples=samples, name=name)
        raise PulseError(
            "The first argument must be an integer value representing "
            "duration."
        )

    return to_pulse


def _update_annotations(discretized_pulse: Callable) -> Callable:
    """Update annotations of a discretized pulse function.

    Args:
        discretized_pulse: Discretized decorated continuous pulse.
    """
    undecorated_annotations = list(discretized_pulse.__annotations__.items())
    decorated_annotations = undecorated_annotations[1:]
    decorated_annotations.insert(0, ("duration", int))
    discretized_pulse.__annotations__ = dict(decorated_annotations)
    return discretized_pulse


def _update_docstring(
    discretized_pulse: Callable, sampler_inst: Callable
) -> Callable:
    """Update annotations of discretized continuous pulse function.

    Args:
        discretized_pulse: Discretized decorated continuous pulse.
        sampler_inst: Applied sampler.
    """
    wrapped_docstring = pydoc.render_doc(discretized_pulse, "%s")
    header, body = wrapped_docstring.split("\n", 1)
    body = textwrap.indent(body, "                    ")
    wrapped_docstring = header + body
    updated_ds = f"""
                Discretized continuous pulse function:
                `{discretized_pulse.__name__}` using
                sampler: `{sampler_inst.__name__}`.

                 The first argument (time) of the continuous pulse function
                 has been replaced with
                 a discretized `duration` of type (int).

                 Args:
                     duration (int)
                     *args: Remaining arguments of continuous pulse function.
                            See continuous pulse function documentation below.
                     **kwargs: Remaining kwargs of continuous pulse function.
                           See continuous pulse function documentation
                           below.

                 Sampled continuous function:

                    {wrapped_docstring}
                """

    discretized_pulse.__doc__ = updated_ds
    return discretized_pulse


def sampler(sample_function: Callable) -> Callable:
    """Sampler decorator base method.

    Samplers convert a continuous function to a discretized pulse.

    They operate on a function with the signature:
        `def f(times: np.ndarray, *args, **kwargs) -> np.ndarray`
    Where `times` is a numpy array of floats with length ``n_times`` and the
    output array is a complex numpy array with length ``n_times``. The output
    of the decorator is an instance of `FunctionalPulse` with signature:
        `def g(duration: int, *args, **kwargs) -> Waveform`

    Note that if your continuous pulse function outputs a `complex` scalar
    rather than an `np.ndarray`, you should first vectorize it before
    applying a sampler.


    This class implements the sampler boilerplate for the sampler.

    Args:
        sample_function: A sampler function to be decorated.
    """

    def generate_sampler(continuous_pulse: Callable) -> Callable:
        """Return a decorated sampler function."""

        @functools.wraps(continuous_pulse)
        def call_sampler(duration: int, *args, **kwargs) -> np.ndarray:
            """Sample the analytic pulse function.

            Replace the call to the continuous function with a call to the
            sampler applied to the analytic pulse function.
            """
            sampled_pulse = sample_function(
                continuous_pulse, duration, *args, **kwargs
            )
            return np.asarray(sampled_pulse, dtype=np.complex128)

        # Update type annotations for wrapped continuous function to be
        # discrete.
        call_sampler = _update_annotations(call_sampler)
        # Update docstring with that of the sampler and include sampled
        # function documentation.
        call_sampler = _update_docstring(call_sampler, sample_function)
        # Unset wrapped to return base sampler signature
        # but still get rest of benefits of wraps
        # such as __name__, __qualname__
        call_sampler.__dict__.pop("__wrapped__")
        # wrap with functional pulse
        return functional_pulse(call_sampler)

    return generate_sampler


def left(continuous_pulse: Callable) -> Callable:
    r"""Left sampling strategy decorator.

    See `pulse.samplers.sampler` for more information.

    For `duration`, return:
        $$\{f(t) \in \mathbb{C} | t \in \mathbb{Z}
        \wedge 0<=t<\texttt{duration}\}$$

    Args:
        continuous_pulse: To sample.
    """
    return sampler(strategies.left_sample)(continuous_pulse)


def right(continuous_pulse: Callable) -> Callable:
    r"""Right sampling strategy decorator.

    See `pulse.samplers.sampler` for more information.

    For `duration`, return:
        $$\{f(t) \in \mathbb{C} | t \in \mathbb{Z}
        \wedge 0<t<=\texttt{duration}\}$$

    Args:
        continuous_pulse: To sample.
    """
    return sampler(strategies.right_sample)(continuous_pulse)


def midpoint(continuous_pulse: Callable) -> Callable:
    r"""Midpoint sampling strategy decorator.

    See `pulse.samplers.sampler` for more information.

    For `duration`, return:
        $$\{f(t+0.5) \in \mathbb{C} | t \in \mathbb{Z}
        \wedge 0<=t<\texttt{duration}\}$$

    Args:
        continuous_pulse: To sample.
    """
    return sampler(strategies.midpoint_sample)(continuous_pulse)
