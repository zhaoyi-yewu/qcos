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

import json

from qcos.common.constant import Constant


class StLibrary:
    """ST Library"""

    @staticmethod
    def get_results(client, job_id):
        _status_code, _reason, _text, _response = client.get_job_results(
            job_id
        )
        job_result = json.loads(_text)
        job_status = job_result["result"]["job_status"]
        if job_status in [
            Constant.JOB_STATUS_COMPLETED,
            Constant.JOB_STATUS_FAILED,
            Constant.JOB_STATUS_CANCELLED,
        ]:
            return True
        return False
