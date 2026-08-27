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

from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from .base import BaseWeigher

logger = logging.getLogger(__name__)


class DeviceLoadWeigher(BaseWeigher):
    """Weigh devices by load (queue + running jobs).

    Devices with fewer queued and running jobs get higher weight.
    Weight = -(queued_job_count + running_job_count)
    """

    multiplier = 1.0

    def _weigh_object(self, obj: DeviceState, spec: RequestSpec) -> float:
        total_jobs = (
            obj.queued_job_count
            + obj.running_job_count
            + obj.vendor_queued_job_count
            + obj.vendor_running_job_count
        )
        logger.debug(
            f"DeviceLoadWeigher: device_name: {obj.name}, "
            f"multiplier: {self.multiplier}. "
            f"total_jobs: {total_jobs}, "
            f"queued_job_count: {obj.queued_job_count}, "
            f"running_job_count: {obj.running_job_count}, "
            f"vendor_queued_job_count: {obj.vendor_queued_job_count}, "
            f"vendor_running_job_count: {obj.vendor_running_job_count}"
        )
        return float(-total_jobs)
