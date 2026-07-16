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

from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from .base import BaseFilter


class QueueLimitFilter(BaseFilter):
    """Filter devices by queue capacity.

    Checks whether the device's queue has reached its max_queued_jobs
    limit. A value of -1 means no limit; 0 means no queuing allowed.
    """

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        if obj.max_queued_jobs < 0:
            # No limit
            return True
        if obj.max_queued_jobs == 0:
            # No queuing allowed
            return obj.queued_job_count == 0
        return obj.queued_job_count < obj.max_queued_jobs
