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

import logging
from dataclasses import dataclass

from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec

logger = logging.getLogger(__name__)


@dataclass
class WeightedDevice:
    """A device with its computed weight."""

    obj: DeviceState
    weight: float


class BaseWeigher:
    """Base class for all weighers.

    Subclasses must implement _weigh_object() to return a weight value
    for a single DeviceState. Higher weight = more preferred.
    The multiplier attribute controls this weigher's overall influence.
    """

    # Weight multiplier, can be overridden by config
    multiplier: float = 1.0

    def weigh_objects(
        self, list_obj: list[DeviceState], spec: RequestSpec
    ) -> dict[DeviceState, float]:
        """Compute weights for all devices.

        Args:
            list_obj: list of DeviceState objects
            spec: request spec

        Returns:
            dict mapping DeviceState to its raw weight.
        """
        return {obj: self._weigh_object(obj, spec) for obj in list_obj}

    def _weigh_object(self, obj: DeviceState, spec: RequestSpec) -> float:
        """Compute weight for a single device.

        Args:
            obj: DeviceState object
            spec: request spec

        Returns:
            weight value (higher is better).
        """
        raise NotImplementedError

    def is_enabled(self, spec: RequestSpec) -> bool:
        """Whether this weigher is enabled for the given spec.

        Args:
            spec: request spec

        Returns:
            True if enabled (default).
        """
        return True


class BaseWeightHandler:
    """Weight handler that aggregates all weighers.

    Inspired by OpenStack Nova WeightHandler.
    """

    def __init__(self, weigher_classes: list[type[BaseWeigher]]):
        """Init weight handler.

        Args:
            weigher_classes: list of weigher classes to instantiate
        """
        self._weighers = [cls() for cls in weigher_classes]

    def get_weighed_objects(
        self, list_obj: list[DeviceState], spec: RequestSpec
    ) -> list[WeightedDevice]:
        """Compute total weight for each device and sort descending.

        Args:
            list_obj: list of DeviceState objects
            spec: request spec

        Returns:
            list of WeightedDevice sorted by weight (highest first).
        """
        # Use index-based approach since DeviceState is not hashable
        # (it contains list/dict fields)
        weights = [0.0] * len(list_obj)

        for weigher in self._weighers:
            if not weigher.is_enabled(spec):
                continue
            for idx, obj in enumerate(list_obj):
                w = weigher._weigh_object(obj, spec)
                weights[idx] += w * weigher.multiplier

        result = [
            WeightedDevice(obj=list_obj[idx], weight=weights[idx])
            for idx in range(len(list_obj))
        ]
        # Sort by weight descending (highest weight = most preferred)
        result.sort(key=lambda x: x.weight, reverse=True)
        return result
