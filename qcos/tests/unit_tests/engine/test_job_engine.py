#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
import numpy as np
import pytest

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock

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
    run_code,
    run_qubo_code,
    run_subqubo_code,
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
        return_value = driver(driver_info, None, None, {"data": {}})
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

    # test _run_code
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

    # test run_code for qasm
    @patch("qcos.engine.job_engine.init_driver.submit")
    @patch("qcos.engine.job_engine.init_transpiler.submit")
    @patch("qcos.engine.job_engine._run_code")
    def test_run_code_normal_flow_qasm(
        self,
        mock_run_code,
        mock_init_transpiler,
        mock_init_driver,
    ):
        mock_driver = Mock(spec=DriverBase)
        mock_driver.name = "TestDriver"
        mock_driver.enable_transpiler = True
        mock_transpiler = Mock(spec=TranspilerBase)
        mock_transpiler.name = "TestTranspiler"
        mock_transpiler.alias_name = "TestAlias"
        mock_init_driver.return_value.result.return_value = {
            "driver": mock_driver,
            "error": None,
        }
        mock_init_transpiler.return_value.result.return_value = {
            "transpiler": mock_transpiler,
            "error": None,
        }
        expected_results = {"results": "test_results"}
        mock_run_code.return_value = (
            expected_results,
            mock_driver,
            mock_transpiler,
            {},
        )
        source_code_index = 0
        src_code_dict = {"key": "value"}
        job_info = {
            "data": {
                "code_type": Constant.CODE_TYPE_QASM,
                "driver_options": {},
                "transpiler_options": None,
            },
            "driver": {"module_name": "test", "class_name": "TestDriver"},
            "transpiler": {
                "module_name": "test",
                "class_name": "TestTranspiler",
            },
            "device": "test_device",
        }
        monitor_info = {"driver": None}
        results, driver, transpiler, mapping_dict = run_code(
            source_code_index,
            src_code_dict,
            job_info,
            None,
            None,
            monitor_info,
        )
        assert results == expected_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        assert mapping_dict == {}
        mock_init_driver.assert_called_once()
        mock_init_transpiler.assert_called_once()
        mock_run_code.assert_called_once()

    # test run_code for qubo
    @patch("qcos.engine.job_engine.init_driver.submit")
    @patch("qcos.engine.job_engine.init_transpiler.submit")
    @patch("qcos.engine.job_engine.run_qubo_code")
    def test_run_code_normal_flow_qubo(
        self, mock_run_qubo_code, mock_init_transpiler, mock_init_driver
    ):
        mock_driver = Mock(spec=DriverBase)
        mock_driver.name = "TestDriver"
        mock_driver.enable_transpiler = False
        mock_init_driver.return_value.result.return_value = {
            "driver": mock_driver,
            "error": None,
        }
        expected_results = {"results": "qubo_results"}
        mock_run_qubo_code.return_value = (
            expected_results,
            mock_driver,
            None,
            {},
        )
        source_code_index = 0
        src_code_dict = {"key": "value"}
        job_info = {
            "data": {
                "code_type": Constant.CODE_TYPE_QUBO,
                "driver_options": {},
            },
            "driver": {"module_name": "test", "class_name": "TestDriver"},
            "device": "test_device",
        }
        monitor_info = {"driver": None}
        results, driver, transpiler, _ = run_code(
            source_code_index,
            src_code_dict,
            job_info,
            None,
            None,
            monitor_info,
        )
        assert results == expected_results
        assert driver == mock_driver
        assert transpiler is None
        mock_init_driver.assert_called_once()
        mock_init_transpiler.assert_not_called()
        mock_run_qubo_code.assert_called_once()

    @patch("qcos.engine.job_engine.check_matrix")
    @patch("qcos.engine.job_engine.check_qubo_matrix_bit_width")
    @patch("qcos.engine.job_engine.qubo_matrix_to_ising_matrix")
    @patch("qcos.engine.job_engine.scale_to_integer_matrix")
    @patch("qcos.engine.job_engine.get_spins_num")
    @patch("qcos.engine.job_engine._run_code")
    @patch("qcos.engine.job_engine.process_qubo_solution")
    def test_run_qubo_code_no_precision_reduction_needed(
        self,
        mock_process_solution,
        mock_run_code,
        mock_get_spins_num,
        mock_scale_matrix,
        mock_ising_matrix,
        mock_check_bit_width,
        mock_check_matrix,
    ):
        job_id = "00000000-0000-4000-8000-000000000001"
        source_code_index = 0
        src_code_index = f"{job_id}-{source_code_index}"
        simple_qubo_matrix = np.array([[1, 0.5], [0.5, 2]])
        src_code_dict = {src_code_index: simple_qubo_matrix}

        job_info = {
            "data": {
                "job_id": job_id,
                "source_code": [simple_qubo_matrix.tolist()],
                "code_type": Constant.CODE_TYPE_QUBO,
            }
        }
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 5
        mock_driver.get_enable_subqubo.return_value = False
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        monitor_info = {"progress": 0}
        mock_check_bit_width.return_value = (True, "")
        mock_check_matrix.return_value = (True, "")
        mock_ising_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_scale_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_get_spins_num.return_value = (
            [1, 1],
            [0, 1, 2],
            2,
        )
        expected_results = {"results": "test_results"}
        mock_run_code.return_value = (
            expected_results,
            mock_driver,
            mock_transpiler,
            {},
        )
        processed_results = {"results": "processed_results"}
        mock_process_solution.return_value = processed_results
        results, driver, transpiler, _ = run_qubo_code(
            source_code_index,
            src_code_dict,
            job_info,
            mock_driver,
            mock_transpiler,
            monitor_info,
        )
        assert results == processed_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_run_code.assert_called_once()
        mock_check_bit_width.assert_called_once()

    @patch("qcos.engine.job_engine.check_matrix")
    @patch("qcos.engine.job_engine.check_qubo_matrix_bit_width")
    @patch("qcos.engine.job_engine.qubo_matrix_to_ising_matrix")
    @patch("qcos.engine.job_engine.scale_to_integer_matrix")
    @patch("qcos.engine.job_engine.get_spins_num")
    @patch("qcos.engine.job_engine._run_code")
    @patch("qcos.engine.job_engine.process_qubo_solution")
    def test_run_qubo_code_subqubo_no_needed(
        self,
        mock_process_solution,
        mock_run_code,
        mock_get_spins_num,
        mock_scale_matrix,
        mock_ising_matrix,
        mock_check_bit_width,
        mock_check_matrix,
    ):
        job_id = "00000000-0000-4000-8000-000000000001"
        source_code_index = 0
        src_code_index = f"{job_id}-{source_code_index}"
        simple_qubo_matrix = np.array([[1, 0.5], [0.5, 2]])
        src_code_dict = {src_code_index: simple_qubo_matrix}
        job_info = {
            "data": {
                "job_id": job_id,
                "source_code": [simple_qubo_matrix.tolist()],
                "code_type": Constant.CODE_TYPE_QUBO,
            }
        }
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 5
        mock_driver.get_enable_subqubo.return_value = True
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        monitor_info = {"progress": 0}
        mock_check_bit_width.return_value = (True, "")
        mock_check_matrix.return_value = (True, "")
        mock_ising_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_scale_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_get_spins_num.return_value = (
            [3, 3],
            [0, 3, 6],
            6,
        )
        processed_results = {"results": "processed_results"}
        mock_process_solution.return_value = processed_results
        expected_results = {"results": "subqubo_results"}
        mock_run_code.return_value = (
            expected_results,
            mock_driver,
            mock_transpiler,
            {},
        )
        results, driver, transpiler, _ = run_qubo_code(
            source_code_index,
            src_code_dict,
            job_info,
            mock_driver,
            mock_transpiler,
            monitor_info,
        )
        assert results == processed_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_run_code.assert_called_once()
        mock_check_bit_width.assert_called_once()

    @patch("qcos.engine.job_engine.check_matrix")
    @patch("qcos.engine.job_engine.check_qubo_matrix_bit_width")
    @patch("qcos.engine.job_engine.qubo_matrix_to_ising_matrix")
    @patch("qcos.engine.job_engine.scale_to_integer_matrix")
    @patch("qcos.engine.job_engine.get_spins_num")
    @patch("qcos.engine.job_engine.run_subqubo_code")
    @patch("qcos.engine.job_engine.process_qubo_solution")
    def test_run_qubo_code_subqubo_needed_and_enabled(
        self,
        mock_process_solution,
        mock_run_subqubo_code,
        mock_get_spins_num,
        mock_scale_matrix,
        mock_ising_matrix,
        mock_check_bit_width,
        mock_check_matrix,
    ):
        job_id = "00000000-0000-4000-8000-000000000001"
        source_code_index = 0
        src_code_index = f"{job_id}-{source_code_index}"
        simple_qubo_matrix = np.array([[1, 0.5], [0.5, 2]])
        src_code_dict = {src_code_index: simple_qubo_matrix}
        job_info = {
            "data": {
                "job_id": job_id,
                "source_code": [simple_qubo_matrix.tolist()],
                "code_type": Constant.CODE_TYPE_QUBO,
            }
        }
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_subqubo.return_value = True
        mock_driver.get_name.return_value = "TestDevice"
        mock_driver.get_enable_subqubo.return_value = True
        mock_transpiler = Mock()
        monitor_info = {"progress": 0}
        mock_check_bit_width.return_value = (True, "")
        mock_check_matrix.return_value = (True, "")
        mock_ising_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_scale_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_get_spins_num.return_value = ([3, 3], [0, 3, 6], 6)
        expected_results = {"results": "subqubo_results"}
        mock_run_subqubo_code.return_value = (
            expected_results,
            mock_driver,
            mock_transpiler,
            {},
        )
        processed_results = {"results": "processed_results"}
        mock_process_solution.return_value = processed_results
        results, driver, transpiler, _ = run_qubo_code(
            source_code_index,
            src_code_dict,
            job_info,
            mock_driver,
            mock_transpiler,
            monitor_info,
        )
        assert results == expected_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_run_subqubo_code.assert_called_once()
        mock_check_bit_width.assert_called_once()

    @patch("qcos.engine.job_engine.logger")
    @patch("qcos.engine.job_engine._run_code")
    def test_run_subqubo_code_normal_flow(
        self,
        mock_run_code,
        mock_logger,
    ):
        job_id = "00000000-0000-4000-8000-000000000001"
        source_code_index = 0
        src_code_index = f"{job_id}-{source_code_index}"
        simple_qubo_matrix = np.array([
            [1, 0.5, 3, 4],
            [0.5, 2, 1, 3],
            [1, 0.5, 3, 4],
            [0.5, 2, 1, 3],
        ])
        src_code_dict = {src_code_index: simple_qubo_matrix}
        job_info = {
            "data": {
                "job_id": job_id,
                "source_code": [simple_qubo_matrix.tolist()],
                "code_type": Constant.CODE_TYPE_QUBO,
            }
        }
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        monitor_info = {"progress": 0}
        max_qubits = 2
        total_spins_num = 5
        sub_job_result = {
            "results": {"out_data": [{"solutionVector": [1, 0, 1, 0]}]}
        }
        mock_run_code.return_value = (
            sub_job_result,
            mock_driver,
            mock_transpiler,
            {},
        )
        results, driver, transpiler, _ = run_subqubo_code(
            max_qubits,
            total_spins_num,
            source_code_index,
            src_code_dict,
            job_info,
            mock_driver,
            mock_transpiler,
            monitor_info,
        )
        assert results == sub_job_result
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_logger.info.assert_called_with("start subqubo")

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
