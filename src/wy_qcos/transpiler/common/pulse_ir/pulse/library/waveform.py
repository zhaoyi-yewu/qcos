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
"""A pulse that is described by complex-valued sample points."""

from __future__ import annotations
from typing import Any

import numpy as np

from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.pulse.library.pulse import Pulse
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


class Waveform(Pulse):
    """A pulse specified completely by complex-valued samples.

    Each sample is played for the duration of the backend cycle time,
    ``dt``.
    """

    @deprecate_pulse_func
    def __init__(
        self,
        samples: np.ndarray | list[complex],
        name: str | None = None,
        epsilon: float = 1e-7,
        limit_amplitude: bool | None = None,
    ):
        """Create new sample pulse command.

        Args:
            samples: Complex array of the samples in the pulse envelope.
            name: Unique name to identify the pulse.
            epsilon: Pulse sample norm tolerance for clipping.
                If any sample's norm exceeds unity by less than or equal to
                ``epsilon``, it will be clipped to unit norm. If the sample
                norm is greater than ``1 + epsilon``, an error is raised.
            limit_amplitude: Passed to parent Pulse
        """
        super().__init__(
            duration=len(samples), name=name, limit_amplitude=limit_amplitude
        )
        sample_array: np.ndarray = np.asarray(samples, dtype=np.complex128)
        self.epsilon = epsilon
        self._samples = self._clip(sample_array, epsilon=epsilon)

    @property
    def samples(self) -> np.ndarray:
        """Return sample values."""
        return self._samples

    def _clip(self, samples: np.ndarray, epsilon: float = 1e-7) -> np.ndarray:
        """Clip samples that are within epsilon of unit norm.

        If the difference is greater than ``epsilon``, an error is raised.

        Args:
            samples: Complex array of the samples in the pulse envelope.
            epsilon: Pulse sample norm tolerance for clipping.
                If any sample's norm exceeds unity by less than or equal to
                ``epsilon``, it will be clipped to unit norm. If the sample
                norm is greater than ``1 + epsilon``, an error is raised.

        Returns:
            Clipped pulse samples.

        Raises:
            PulseError: If there exists a pulse sample with a norm greater
                than ``1 + epsilon``.
        """
        samples_norm = np.abs(samples)
        to_clip = (samples_norm > 1.0) & (samples_norm <= 1.0 + epsilon)

        if np.any(to_clip):
            # first try normalizing by the abs value
            clip_where = np.argwhere(to_clip)
            clip_angle = np.angle(samples[clip_where])
            clipped_samples = np.exp(1j * clip_angle, dtype=np.complex128)

            # if norm still exceed one subtract epsilon
            # required for some platforms
            clipped_sample_norms = np.abs(clipped_samples)
            to_clip_epsilon = clipped_sample_norms > 1.0
            if np.any(to_clip_epsilon):
                clip_where_epsilon = np.argwhere(to_clip_epsilon)
                clipped_samples_epsilon = (1 - epsilon) * np.exp(
                    1j * clip_angle[clip_where_epsilon], dtype=np.complex128
                )
                clipped_samples[clip_where_epsilon] = clipped_samples_epsilon

            # update samples with clipped values
            samples[clip_where] = clipped_samples
            samples_norm[clip_where] = np.abs(clipped_samples)

        if np.any(samples_norm > 1.0) and self._limit_amplitude:
            amp = np.max(samples_norm)
            raise PulseError(
                f"Pulse contains sample with norm {amp} greater than "
                "1+epsilon."
                " This can be overruled by setting Pulse.limit_amplitude."
            )

        return samples

    def is_parameterized(self) -> bool:
        """Return True iff the instruction is parameterized."""
        return False

    @property
    def parameters(self) -> dict[str, Any]:
        """Return a dictionary containing the pulse's parameters."""
        return {}

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Waveform):
            return NotImplemented
        return (
            super().__eq__(other)
            and self.samples.shape == other.samples.shape
            and np.allclose(
                self.samples, other.samples, rtol=0, atol=self.epsilon
            )
        )

    def __hash__(self) -> int:
        return hash(self.samples.tobytes())

    def __repr__(self) -> str:
        opt = np.get_printoptions()
        np.set_printoptions(threshold=50)
        np.set_printoptions(**opt)
        name_repr = f", name='{self.name}'" if self.name is not None else ""
        return f"{self.__class__.__name__}({repr(self.samples)}{name_repr})"
