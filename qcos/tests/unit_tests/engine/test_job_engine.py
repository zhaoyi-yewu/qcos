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

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from qcos.common.constant import Constant
from qcos.drivers.driver_base import DriverBase
from qcos.drivers.dummy.driver_dummy import DriverDummy
from qcos.engine.job_engine import (init_driver, init_transpiler,
                                    driver_cancel, register_signals,
                                    update_progress)
from qcos.engine.job_engine import (
    create_src_code_info,
    update_src_code_info,
    get_src_code_cnt,
    get_internal_aggregated_results,
    get_external_aggregated_results
)
from qcos.engine.job_engine import SourceCodeInfo


class TestJobEngine:
    @classmethod
    def setup_class(cls):
        cls.simple_data = '''
                  OPENQASM 2.0;
                  include "qelib1.inc";
                  qreg q[1];
                  creg c[1];
                  h q[0];
                  x q[0];
                  rx(1) q[0];
                  measure q->c;
                '''

        cls.job_data = {
            "job_id": "00000000-0000-4000-8000-000000000001",
            "source_code": [cls.simple_data],
            "circuit_aggregation": None
        }
        cls.src_code_info = SourceCodeInfo()
        cls.src_code_info.src_code_list = [
            {"00000000-0000-4000-8000-000000000001-0": cls.simple_data}]
        cls.aggregation_info = MagicMock()
        cls.aggregation_info.sub_jobs = {
            "00000000-0000-4000-8000-000000000002-0":
                {"job_info": {"data": {"source_code": cls.simple_data}}},
            "00000000-0000-4000-8000-000000000003-0":
                {"job_info": {"data": {"source_code": cls.simple_data}}}
        }
        cls.job_results = {
            "results": {
                "00000000-0000-4000-8000-000000000002-0": "00",
                "00000000-0000-4000-8000-000000000003-0": "11"},
            "metadata": {"end_date": datetime.now()},
            "profiling": {}
        }
        cls.mapping_dict = {
            "00000000-0000-4000-8000-000000000002-0": 2,
            "00000000-0000-4000-8000-000000000003-0": 2
        }

    @patch.object(DriverBase, "validate_driver_configs")
    def test_init_driver(self, mock_validate_driver_configs):
        driver_info = {"module_name": "name", "class_name": "DriverDummy"}
        mock_run = Mock()
        mock_run.name = DriverDummy()
        mock_validate_driver_configs.return_value = iter([True, "err_msg"])

        driver = init_driver.fn
        driver(driver_info, None, None)

    def test_init_transpiler(self):
        transpiler_info = {"module_name": "name",
                           "class_name": "TranspilerDummy"}

        transpiler = init_transpiler.fn
        transpiler(transpiler_info, None)

    def test_create_src_code_info_with_none_aggregation(self):
        result = create_src_code_info(self.job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_NONE
        assert len(result.src_code_list) == 1

    def test_create_src_code_info_with_aggregation(self):
        self.job_data["circuit_aggregation"] = (
            Constant.AGGREGATION_TYPE_EXTERNAL)
        result = create_src_code_info(self.job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL
        assert len(result.src_code_list) == 1

    def test_update_src_code_info(self):
        self.job_data["circuit_aggregation"] = (
            Constant.AGGREGATION_TYPE_EXTERNAL)
        result = create_src_code_info(self.job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL
        assert len(result.src_code_list) == 1
        result = update_src_code_info(
            self.src_code_info, self.aggregation_info)
        assert len(result.src_code_list) == 1

    def test_get_src_code_cnt(self):
        self.src_code_info.src_code_list = [
            {"key1": "value1"}, {"key2": "value2"}]
        result = get_src_code_cnt(self.src_code_info)
        assert result == 2

    def test_get_internal_aggregated_results(self):
        result = get_internal_aggregated_results(
            self.job_results, self.mapping_dict)
        assert len(result) == 2
        assert result[0]["num_qubits"] == 2
        assert result[1]["num_qubits"] == 2

    def test_get_external_aggregated_results(self):
        result = get_external_aggregated_results(
            self.job_results, self.mapping_dict)

        assert len(result["sub_results"]) == 1

    def test_driver_cancel(self):
        driver_cancel("111", DriverDummy)

    def test_register_signals(self):
        register_signals("111", {"driver": DriverDummy})

    @patch('qcos.engine.job_engine.update_progress_artifact')
    def test_update_progress(self, mock_update_progress_artifact):
        mock_update_progress_artifact.return_value = None
        update_progress("id", "progress")
