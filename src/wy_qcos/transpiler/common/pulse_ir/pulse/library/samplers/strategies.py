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
"""Sampler strategy module for sampler functions.

Sampler functions have signature.
    ```python
    def sampler_function(
        continuous_pulse: Callable, duration: int, *args, **kwargs
    ) -> np.ndarray: ...
    ```
where the supplied `continuous_pulse` is a function with signature:
    ```python
    def f(times: np.ndarray, *args, **kwargs) -> np.ndarray: ...
    ```
The sampler calls the `continuous_pulse` function with a set of times
chosen by its sampling strategy, along with the passed `args` and
`kwargs`.
"""

from collections.abc import Callable

import numpy as np


def left_sample(
    continuous_pulse: Callable, duration: int, *args, **kwargs
) -> np.ndarray:
    """Left sample a continuous function.

    Args:
        continuous_pulse: Continuous pulse function to sample.
        duration: Duration to sample for.
        *args: Continuous pulse function args.
        **kwargs: Continuous pulse function kwargs.
    """
    times = np.arange(duration)
    return continuous_pulse(times, *args, **kwargs)


def right_sample(
    continuous_pulse: Callable, duration: int, *args, **kwargs
) -> np.ndarray:
    """Sampling strategy for decorator.

    Args:
        continuous_pulse: Continuous pulse function to sample.
        duration: Duration to sample for.
        *args: Continuous pulse function args.
        **kwargs: Continuous pulse function kwargs.
    """
    times = np.arange(1, duration + 1)
    return continuous_pulse(times, *args, **kwargs)


def midpoint_sample(
    continuous_pulse: Callable, duration: int, *args, **kwargs
) -> np.ndarray:
    """Sampling strategy for decorator.

    Args:
        continuous_pulse: Continuous pulse function to sample.
        duration: Duration to sample for.
        *args: Continuous pulse function args.
        **kwargs: Continuous pulse function kwargs.
    """
    times = np.arange(1 / 2, duration + 1 / 2)
    return continuous_pulse(times, *args, **kwargs)
