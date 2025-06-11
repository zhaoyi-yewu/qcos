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

import logging

from drivers.driver_base import DriverBase


logger = logging.getLogger(__name__)


class DriverPassthrough(DriverBase):
    """
    Passthrough driver
    """

    def __init__(self):
        super(DriverPassthrough, self).__init__()
        self.version = "0.0.1"
        self.enable_transpiler = False

    def init_driver(self):
        """
        Init driver
        """
        pass

    def close_driver(self):
        """
        Close driver
        """
        pass

    def run(self, job_id, data, data_type, shots=1):
        """
        Run job

        :params job_id: job ID
        :params data: data
        :params data_type: data type
        :params shots: shots
        """
        logger.info(f"job_id: {job_id}, data_type: {data_type}, data: {data},"
                    f" shots: {shots}")
