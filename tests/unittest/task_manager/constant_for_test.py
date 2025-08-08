
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.common.constant import Constant
from qcos.common.library import Library


class ConstantForTest:
    args = {'job_info': {'data': {
        "enable_circuit_aggregation": True,
        "job_id": '00000000-0000-4000-8000-000000000001',
        "job_name": 'job_name',
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_sched_policy": Constant.DEFAULT_JOB_SCHED_POLICY,
        "job_priority": 1,
        "description": 'description',
        "backend": Constant.DRIVER_DUMMY,
        "transpiler": Constant.TRANSPILERS,
        "transpiler_info": {},
        "shots": 10,
        "profiling": Constant.PROFILING_TYPES,
        "callbacks": [],
        "dry_run": True,
        "creation_date": Library.get_current_datetime(),
        "end_date": Library.get_current_datetime()}}}

    job_info = {
        "job_id": '00000000-0000-4000-8000-000000000001',
        "job_name": 'job_name',
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_sched_policy": Constant.DEFAULT_JOB_SCHED_POLICY,
        "job_priority": 1,
        "description": 'description',
        "backend": Constant.DRIVER_DUMMY,
        "transpiler": Constant.TRANSPILERS,
        "transpiler_info": {},
        "shots": 10,
        "profiling": Constant.PROFILING_TYPES,
        "callbacks": [],
        "dry_run": True,
        "creation_date": Library.get_current_datetime(),
        "end_date": Library.get_current_datetime()
    }
    flow_info = {
        "deploy_name": Constant.DRIVER_DUMMY,
        "deploy_flow_func": "",
        "deploy_flow_path": "../engine/job_engine.py"
    }
    job_id = "00000000-0000-4000-8000-000000000001"
    job_ids = ['00000000-0000-4000-8000-000000000001',
               '00000000-0000-4000-8000-000000000002',
               '00000000-0000-4000-8000-000000000003']
