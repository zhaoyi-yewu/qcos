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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------


class Constant(object):
    """
    Constants
    """
    # Code Types
    code_type_qasm2 = "QASM2"
    code_type_qasm3 = "QASM3"
    code_type_qubo = "QUBO"
    code_types = [code_type_qasm2, code_type_qasm3, code_type_qubo]

    # Plugins
    plugin_qc = "PluginQC"
    plugin_types = [plugin_qc]

    # Drivers
    qc_driver_dummy = "QcDummyDriver"
    qc_driver_types = [qc_driver_dummy]

    # Job Types
    job_type_estimation = "estimation"
    job_type_sampling = "sampling"
    job_types = [job_type_estimation, job_type_sampling]

    # Job Status
    job_status_unknown = "UNKNOWN"
    job_status_queued = "QUEUED"
    job_status_running = "RUNNING"
    job_status_failed = "FAILED"
    job_status_completed = "COMPLETED"
    job_status_cancelling = "CANCELLING"
    job_status_cancelled = "CANCELLED"
    job_statuses = [job_status_unknown, job_status_queued, job_status_running,
                    job_status_failed, job_status_completed,
                    job_status_cancelling, job_status_cancelled]
