#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase
from qcos.drivers.dummy.driver_dummy import DriverDummy
from qcos.engine.job_engine import (
    init_driver,
    init_transpiler,
    job_flow,
    driver_cancel,
    register_signals,
    update_progress,
    _run_code,
    flow_parse,
    flow_transpile,
    flow_task_monitor,
    flow_run_driver,
    create_src_code_info,
    update_src_code_info,
    get_src_code_cnt,
    get_internal_aggregated_results,
    get_external_aggregated_results,
    format_run_results,
    format_error_results,
    task_monitor,
    parse,
    transpile,
    driver_run,
    run_job_callback,
)
from qcos.engine.job_engine import SourceCodeInfo
from qcos.transpiler.transpiler_base import TranspilerBase


class TestJobEngine:
    @classmethod
    def setup_class(cls):
        cls.simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """

        cls.job_data = {
            "job_id": "00000000-0000-4000-8000-000000000001",
            "source_code": [cls.simple_data],
            "circuit_aggregation": None,
            "profiling": [],
        }
        cls.job_info = {
            "data": cls.job_data,
            "driver": {
                "module_name": "qcos.drivers.dummy.driver_dummy",
                "class_name": "DriverDummy",
            },
            "driver_options": None,
            "device": "dummy",
            "transpiler": {
                "module_name": "qcos.transpiler.cmss.transpiler_cmss",
                "class_name": "TranspilerCmss",
            },
            "transpiler_options": "dummy",
        }
        cls.src_code_info = SourceCodeInfo()
        cls.src_code_info.src_code_list = [
            {"00000000-0000-4000-8000-000000000001-0": cls.simple_data}
        ]
        cls.aggregation_info = MagicMock()
        cls.aggregation_info.sub_jobs = {
            "00000000-0000-4000-8000-000000000002-0": {
                "job_info": {"data": {"source_code": cls.simple_data}}
            },
            "00000000-0000-4000-8000-000000000003-0": {
                "job_info": {"data": {"source_code": cls.simple_data}}
            },
        }
        cls.job_results = {
            "results": {
                "00000000-0000-4000-8000-000000000002-0": "00",
                "00000000-0000-4000-8000-000000000003-0": "11",
            },
            "metadata": {"end_date": datetime.now()},
            "profiling": {},
        }
        cls.mapping_dict = {
            "00000000-0000-4000-8000-000000000002-0": 2,
            "00000000-0000-4000-8000-000000000003-0": 2,
        }
        cls.artifact_id = "00000001-0000-4000-8000-000000000001"

    @patch("qcos.engine.job_engine.getattr")
    @patch("qcos.engine.job_engine.importlib.import_module")
    @patch.object(DriverBase, "validate_driver_configs")
    def test_init_driver(
        self, mock_validate_driver_configs, mock_importlib, mock_getattr
    ):
        driver_info = {"module_name": "name", "class_name": "DriverDummy"}
        mock_importlib.return_value = DriverDummy
        mock_getattr.return_value = DriverDummy

        mock_validate_driver_configs.return_value = iter([True, "err_msg"])

        driver = init_driver.fn
        return_value = driver(driver_info, None, None)
        assert return_value["driver"] is None

    def test_init_transpiler(self):
        transpiler_info = {
            "module_name": "name",
            "class_name": "TranspilerDummy",
        }

        transpiler = init_transpiler.fn
        return_value = transpiler(transpiler_info, None)
        assert return_value["transpiler"] is None

    def test_create_src_code_info_with_none_aggregation(self):
        result = create_src_code_info(self.job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_NONE
        assert len(result.src_code_list) == 1

    def test_create_src_code_info_with_aggregation(self):
        self.job_data["circuit_aggregation"] = (
            Constant.AGGREGATION_TYPE_EXTERNAL
        )
        result = create_src_code_info(self.job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL
        assert len(result.src_code_list) == 1

    def test_update_src_code_info(self):
        self.job_data["circuit_aggregation"] = (
            Constant.AGGREGATION_TYPE_EXTERNAL
        )
        result = create_src_code_info(self.job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL
        assert len(result.src_code_list) == 1
        result = update_src_code_info(
            self.src_code_info, self.aggregation_info
        )
        assert len(result.src_code_list) == 1

    def test_get_src_code_cnt(self):
        self.src_code_info.src_code_list = [
            {"key1": "value1"},
            {"key2": "value2"},
        ]
        result = get_src_code_cnt(self.src_code_info)
        assert result == 2

    def test_get_internal_aggregated_results(self):
        result = get_internal_aggregated_results(
            self.job_results, self.mapping_dict
        )
        assert len(result) == 2
        assert result[0]["num_qubits"] == 2
        assert result[1]["num_qubits"] == 2

    def test_get_external_aggregated_results(self):
        result = get_external_aggregated_results(
            self.job_results, self.mapping_dict
        )

        assert len(result["sub_results"]) == 1

    def test_driver_cancel(self):
        assert driver_cancel(self.job_data["job_id"], DriverDummy) is None

    def test_register_signals(self):
        assert (
            register_signals(self.job_data["job_id"], {"driver": DriverDummy})
            is None
        )

    @patch("qcos.engine.job_engine.update_progress_artifact")
    def test_update_progress(self, mock_update_progress_artifact):
        mock_update_progress_artifact.return_value = None
        assert update_progress("id", "progress") is None

    @patch("qcos.engine.job_engine.flow_run_driver")
    @patch("qcos.engine.job_engine.flow_transpile")
    @patch("qcos.engine.job_engine.flow_parse")
    def test_run_code(
        self, mock_flow_parse, mock_flow_transpile, mock_flow_run_driver
    ):
        mock_flow_parse.return_value = iter([{"parsed_src_code": "v"}, 233])
        mock_flow_transpile.return_value = ({}, 466)
        with pytest.raises(ValueError) as e:
            _run_code(
                [1, 2, 3], {}, {"data": {}}, DriverBase(), TranspilerBase(), {}
            )
        assert str(e.value) == "unexpected transpile_results or num_qubits"

        mock_flow_parse.return_value = iter([{"parsed_src_code": "v"}, 233])
        mock_flow_transpile.return_value = (
            {"transpile_results": "s", "num_qubits": "6"},
            466,
        )
        mock_flow_run_driver.return_value = iter([
            {"results": "v", "metadata": "m"},
            233,
        ])
        _run_code(
            [1, 2, 3], {}, {"data": {}}, DriverBase(), TranspilerBase(), {}
        )

    @patch("qcos.engine.job_engine.parse.submit")
    def test_flow_parse(self, mock_parse):
        mock_parse.return_value = Mock()
        result, _ = flow_parse({}, TranspilerBase(), Constant.PROFILING_TYPES)
        assert isinstance(result, Mock) is True

    @patch("qcos.engine.job_engine.transpile.submit")
    def test_flow_transpile(self, mock_transpile):
        mock_transpile.return_value = Mock()
        result, _ = flow_transpile(
            "", TranspilerBase(), DriverBase(), Constant.PROFILING_TYPES
        )
        assert isinstance(result, Mock) is True

    @patch("qcos.engine.job_engine.task_monitor.submit")
    def test_flow_task_monitor(self, mock_task_monitor):
        mock_task_monitor.return_value = None
        assert flow_task_monitor("") is None

    @patch("qcos.engine.job_engine.driver_run.submit")
    def test_flow_run_driver(self, mock_driver_run):
        mock_driver_run.return_value = Mock()
        result, _ = flow_run_driver(
            {}, 6, DriverBase(), {}, Constant.PROFILING_TYPES
        )
        assert isinstance(result, Mock) is True

    @patch.object(DriverBase, "get_results")
    def test_format_run_results(self, mock_get_results):
        mock_get_results.return_value = "result"
        driver = DriverDummy()
        driver.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
        results = format_run_results(driver, self.job_data["job_id"], 0)
        assert results["results"] == "result"

    def test_format_error_results(self):
        driver = DriverDummy()
        mock_client = Mock()
        results = format_error_results(driver, mock_client, 0)
        assert results["results"] is None

    @patch.object(Library, "async_run_callbacks")
    @patch.object(Library, "get_nested_dict_value")
    def test_job_callback(
        self, mock_get_nested_dict_value, mock_async_run_callbacks
    ):
        mock_get_nested_dict_value.return_value = "value"
        mock_async_run_callbacks.return_value = None, None
        flow_run = Mock()
        state = Mock()
        state.name = Constant.PREFECT_STATE_CANCELLING
        flow_run.name = self.job_data["job_id"]
        flow_run.parameters = "parameters"
        flow_run.state = Mock()
        assert (
            asyncio.run(
                Library.job_callback("flow", flow_run, state, results=[])
            )
            is None
        )

    @patch("qcos.engine.job_engine.update_progress")
    def test_task_monitor(self, mock_update_progress):
        mock_update_progress.return_value = None
        monitor_info = {
            "running": False,
            "driver": DriverBase(),
            "progress": 30,
            "source_code_count": 2,
            "artifact_id": "test_artifact",
        }
        assert task_monitor.fn(monitor_info) is None

    def test_parse(self):
        return_value = parse.fn([], TranspilerBase())
        assert return_value["parsed_src_code"] is None

    def test_transpile(self):
        return_value = transpile.fn([], DriverBase, TranspilerBase())
        assert return_value["transpile_results"] is None

    def test_driver_run(self):
        return_value = driver_run.fn([], DriverBase, 5, self.job_data)
        assert return_value["results"] is None

    @patch("qcos.engine.job_engine.register_signals")
    @patch("qcos.engine.job_engine.create_progress_artifact")
    @patch("qcos.engine.job_engine.flow_task_monitor")
    @patch("qcos.engine.job_engine.run_code")
    def test_job_flow(
        self,
        mock_run_code,
        mock_flow_task_monitor,
        mock_create_progress_artifact,
        mock_register_signals,
    ):
        mock_run_code.return_value = (
            self.job_results,
            None,
            None,
            self.mapping_dict,
        )
        mock_flow_task_monitor.return_value = None
        mock_register_signals.return_values = None
        mock_create_progress_artifact.return_value = self.artifact_id
        self.src_code_info.aggregation_type = Constant.AGGREGATION_TYPE_NONE
        raw_job_flow_func = job_flow.__wrapped__
        self.job_info["data"]["circuit_aggregation"] = None
        self.job_info["data"]["profiling"] = [
            Constant.PROFILING_TYPE_CODE,
            Constant.PROFILING_TYPE_SCHEDULING,
            Constant.PROFILING_TYPE_DRIVER_PARSE,
            Constant.PROFILING_TYPE_DRIVER_TRANSPILE,
            Constant.PROFILING_TYPE_DRIVER_RUN,
        ]
        self.job_info["data"]["code_type"] = Constant.CODE_TYPE_QASM
        self.job_info["data"]["driver_options"] = {}
        job_results_list = raw_job_flow_func(self.job_info)
        assert len(job_results_list) == len(
            self.job_info["data"]["source_code"]
        )
        assert job_results_list[0] == self.job_results
        mock_run_code.assert_called_once()
        mock_create_progress_artifact.assert_called_once()
        assert (
            self.src_code_info.aggregation_type
            == Constant.AGGREGATION_TYPE_NONE
        )

    def test_run_job_callback(self):
        mock_job_callback = AsyncMock()
        Library.job_callback = mock_job_callback

        mock_flow = Mock()
        mock_flow.name = "test_flow"
        mock_flow_run = Mock()
        mock_flow_run.id = "flow_run_123"
        mock_state = Mock()
        mock_state.name = "Completed"
        mock_flow_run.state = mock_state
        mock_context = Mock()
        mock_context.flow = mock_flow
        mock_context.flow_run = mock_flow_run

        job_results_list = None
        _job_results_list = run_job_callback(mock_context, job_results_list)
