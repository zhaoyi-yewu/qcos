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

import numpy as np
import pytest

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from wy_qcos.common.constant import Constant
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.dummy.driver_dummy import DriverDummy
from wy_qcos.engine.job_engine import (
    _run_code,
    attach_fidelity_benchmark,
    counts_to_probs,
    create_src_code_info,
    driver_cancel,
    driver_run,
    flow_parse,
    flow_run_driver,
    flow_task_monitor,
    flow_transpile,
    format_error_results,
    format_run_results,
    get_external_aggregated_results,
    get_internal_aggregated_results,
    get_src_code_cnt,
    init_driver,
    init_transpiler,
    job_flow,
    parse,
    probs_to_dict,
    register_signals,
    run_circuit_code,
    run_circuit_cutting_code,
    run_code,
    run_qubo_code,
    run_subqubo_code,
    split_dict,
    task_monitor,
    transpile,
    update_src_code_info,
)
from wy_qcos.engine.job_engine import SourceCodeInfo
from wy_qcos.transpiler.transpiler_base import TranspilerBase


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
                "module_name": "wy_qcos.driver.dummy.driver_dummy",
                "class_name": "DriverDummy",
            },
            "driver_options": None,
            "device": "dummy",
            "transpiler": {
                "module_name": "wy_qcos.transpiler.cmss.transpiler_cmss",
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
                "job_info": {
                    "data": {
                        "source_code": [cls.simple_data],
                        "flow_run_id": "flow-run-0002",
                    }
                }
            },
            "00000000-0000-4000-8000-000000000003-0": {
                "job_info": {
                    "data": {
                        "source_code": [cls.simple_data],
                        "flow_run_id": "flow-run-0003",
                    }
                }
            },
        }
        cls.job_results = {
            "results": {
                "00000000-0000-4000-8000-000000000002-0": "00",
                "00000000-0000-4000-8000-000000000003-0": "11",
            },
            "metadata": {"ended_at": datetime.now()},
            "profiling": {},
        }
        cls.mapping_dict = {
            "00000000-0000-4000-8000-000000000002-0": 2,
            "00000000-0000-4000-8000-000000000003-0": 2,
        }
        cls.artifact_id = "00000001-0000-4000-8000-000000000001"

    @patch("wy_qcos.engine.job_engine.getattr")
    @patch("wy_qcos.engine.job_engine.importlib.import_module")
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
        transpiler_inst = init_transpiler.fn
        return_value = transpiler_inst(transpiler_info, None)
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

    @pytest.mark.smoke
    @patch("wy_qcos.engine.job_engine.flow_run_driver")
    @patch("wy_qcos.engine.job_engine.flow_transpile")
    @patch("wy_qcos.engine.job_engine.flow_parse")
    def test_run_code(
        self, mock_flow_parse, mock_flow_transpile, mock_flow_run_driver
    ):
        parse_profiling = {
            "parse_started_at": 1.0,
            "parse_ended_at": 2.0,
            "parse_duration": 1.0,
        }
        transpile_profiling = {
            "transpile_started_at": 1.0,
            "transpile_ended_at": 2.0,
            "transpile_duration": 1.0,
        }
        driver_run_profiling = {
            "driver_run_started_at": 1.0,
            "driver_run_ended_at": 2.0,
            "driver_run_duration": 1.0,
        }
        mock_flow_parse.return_value = iter([
            {"parsed_src_code": "v"},
            parse_profiling,
        ])
        mock_flow_transpile.return_value = ({}, transpile_profiling)
        with pytest.raises(ValueError) as exc_info:
            _run_code(
                0,
                {"0-0": self.simple_data},
                {"data": {"code_type": Constant.CODE_TYPE_QASM2}},
                DriverBase(),
                TranspilerBase(),
            )
        assert (
            str(exc_info.value) == "unexpected transpile_results or num_qubits"
        )

        mock_flow_parse.return_value = iter([
            {"parsed_src_code": "v"},
            parse_profiling,
        ])
        mock_flow_transpile.return_value = (
            {"transpile_results": "s", "num_qubits": "6"},
            transpile_profiling,
        )
        mock_flow_run_driver.return_value = iter([
            {"results": "v", "metadata": "m"},
            driver_run_profiling,
        ])
        _run_code(
            0,
            {"0-0": self.simple_data},
            {"data": {"code_type": Constant.CODE_TYPE_QASM2}},
            DriverBase(),
            TranspilerBase(),
        )

    @patch("wy_qcos.engine.job_engine.init_driver.submit")
    @patch("wy_qcos.engine.job_engine.init_transpiler.submit")
    @patch("wy_qcos.engine.job_engine.run_circuit_code")
    def test_run_code_normal_flow_qasm(
        self,
        mock_run_circuit_code,
        mock_init_transpiler,
        mock_init_driver,
    ):
        mock_driver = Mock(spec=DriverBase)
        mock_driver.name = "TestDriver"
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
        mock_run_circuit_code.return_value = (
            expected_results,
            mock_driver,
            mock_transpiler,
            {},
        )
        source_code_index = 0
        src_code_dict = {"00000000-0000-4000-8000-000000000001-0": "value"}
        job_info = {
            "data": {
                "job_id": "00000000-0000-4000-8000-000000000001",
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
        mock_run_circuit_code.assert_called_once()

    @patch("wy_qcos.engine.job_engine.init_driver.submit")
    @patch("wy_qcos.engine.job_engine.init_transpiler.submit")
    @patch("wy_qcos.engine.job_engine.run_qubo_code")
    def test_run_code_normal_flow_qubo(
        self, mock_run_qubo_code, mock_init_transpiler, mock_init_driver
    ):
        mock_driver = Mock(spec=DriverBase)
        mock_driver.name = "TestDriver"
        mock_init_driver.return_value.result.return_value = {
            "driver": mock_driver,
            "error": None,
        }
        mock_transpiler = Mock(spec=TranspilerBase)
        mock_transpiler.name = "TestTranspiler"
        mock_transpiler.alias_name = "TestAlias"
        mock_init_transpiler.return_value.result.return_value = {
            "transpiler": mock_transpiler,
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
            mock_transpiler,
            monitor_info,
        )
        assert results == expected_results
        assert driver == mock_driver
        assert transpiler is None
        mock_init_driver.assert_called_once()
        mock_init_transpiler.assert_not_called()
        mock_run_qubo_code.assert_called_once()

    @patch("wy_qcos.engine.job_engine.check_matrix")
    @patch("wy_qcos.engine.job_engine.check_qubo_matrix_bit_width")
    @patch("wy_qcos.engine.job_engine.qubo_matrix_to_ising_matrix")
    @patch("wy_qcos.engine.job_engine.scale_to_integer_matrix")
    @patch("wy_qcos.engine.job_engine.get_spins_num")
    @patch("wy_qcos.engine.job_engine._run_code")
    @patch("wy_qcos.engine.job_engine.process_qubo_solution")
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
        mock_driver.get_enable_prec_reduce.return_value = True
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        mock_check_bit_width.return_value = (True, "")
        mock_check_matrix.return_value = (True, "")
        mock_ising_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_scale_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_get_spins_num.return_value = ([1, 1], [0, 1, 2], 2)
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
        )
        assert results == processed_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_run_code.assert_called_once()
        mock_check_bit_width.assert_called_once()

    @patch("wy_qcos.engine.job_engine.check_matrix")
    @patch("wy_qcos.engine.job_engine.check_qubo_matrix_bit_width")
    @patch("wy_qcos.engine.job_engine.qubo_matrix_to_ising_matrix")
    @patch("wy_qcos.engine.job_engine.scale_to_integer_matrix")
    @patch("wy_qcos.engine.job_engine.get_spins_num")
    @patch("wy_qcos.engine.job_engine._run_code")
    @patch("wy_qcos.engine.job_engine.process_qubo_solution")
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
        mock_driver.get_enable_prec_reduce.return_value = True
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        mock_check_bit_width.return_value = (True, "")
        mock_check_matrix.return_value = (True, "")
        mock_ising_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_scale_matrix.return_value = np.array([[0, 1], [1, 0]])
        mock_get_spins_num.return_value = ([3, 3], [0, 3, 6], 6)
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
        )
        assert results == processed_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_run_code.assert_called_once()
        mock_check_bit_width.assert_called_once()

    @patch("wy_qcos.engine.job_engine.check_matrix")
    @patch("wy_qcos.engine.job_engine.check_qubo_matrix_bit_width")
    @patch("wy_qcos.engine.job_engine.qubo_matrix_to_ising_matrix")
    @patch("wy_qcos.engine.job_engine.scale_to_integer_matrix")
    @patch("wy_qcos.engine.job_engine.get_spins_num")
    @patch("wy_qcos.engine.job_engine.run_subqubo_code")
    @patch("wy_qcos.engine.job_engine.process_qubo_solution")
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
        mock_driver.get_enable_prec_reduce.return_value = True
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
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
        )
        assert results == expected_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_run_subqubo_code.assert_called_once()
        mock_check_bit_width.assert_called_once()

    @patch("wy_qcos.engine.job_engine._run_code")
    def test_run_subqubo_code_normal_flow(self, mock_run_code):
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
        )
        assert results == sub_job_result
        assert driver == mock_driver
        assert transpiler == mock_transpiler

    def test_counts_to_probs_basic(self):
        count_dict = {"00": 500, "11": 500}
        probs = counts_to_probs(count_dict)
        assert len(probs) == 4
        assert probs[0] == 0.5
        assert probs[3] == 0.5
        assert probs[1] == 0.0
        assert probs[2] == 0.0

    def test_counts_to_probs_empty_dict(self):
        probs = counts_to_probs({})
        assert len(probs) == 0

    def test_counts_to_probs_all_zeros(self):
        probs = counts_to_probs({"00": 0, "01": 0})
        assert len(probs) == 4
        assert all(p == 0.0 for p in probs)

    def test_counts_to_probs_three_qubits(self):
        count_dict = {"000": 250, "111": 750}
        probs = counts_to_probs(count_dict)
        assert len(probs) == 8
        assert probs[0] == 0.25
        assert probs[7] == 0.75

    def test_probs_to_dict_basic(self):
        prob_array = [0.5, 0.0, 0.0, 0.5]
        result = probs_to_dict(prob_array)
        assert len(result) == 2
        assert result["00"] == 0.5
        assert result["11"] == 0.5
        assert "01" not in result
        assert "10" not in result

    def test_probs_to_dict_empty_array(self):
        result = probs_to_dict([])
        assert not result

    def test_probs_to_dict_none_array(self):
        result = probs_to_dict(None)
        assert not result

    def test_probs_to_dict_with_small_values(self):
        prob_array = [0.5, 1e-13, 1e-12, 0.5]
        result = probs_to_dict(prob_array)
        assert len(result) == 2
        assert result["00"] == 0.5
        assert result["11"] == 0.5

    def test_probs_to_dict_with_non_power_of_two(self):
        prob_array = [0.3, 0.3, 0.4]
        result = probs_to_dict(prob_array)
        assert len(result) == 3
        assert result["00"] == 0.3
        assert result["01"] == 0.3
        assert result["10"] == 0.4

    @patch("wy_qcos.engine.job_engine._run_code")
    def test_run_circuit_code_within_limit(self, mock_run_code):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_wirecut.return_value = False
        mock_driver.get_wirecut_qubit_width.return_value = 2
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        mock_transpiler.parse.return_value = {
            "00000000-0000-4000-8000-000000000001-0": (2, None)
        }
        expected_results = {
            "results": {"00": 0.5, "11": 0.5},
            "metadata": {"status": "COMPLETED"},
        }
        source_code_index = 0
        src_code_dict = {"00000000-0000-4000-8000-000000000001-0": "value"}
        mock_run_code.return_value = (
            expected_results,
            mock_driver,
            mock_transpiler,
            {},
        )
        job_info = {
            "data": {
                "job_id": "00000000-0000-4000-8000-000000000001",
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
        results, driver, transpiler, mapping = run_circuit_code(
            source_code_index,
            src_code_dict,
            job_info,
            mock_driver,
            mock_transpiler,
        )
        assert results == expected_results
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        assert mapping == {}
        mock_run_code.assert_called_once()

    def test_attach_fidelity_benchmark_reports_invalid_distribution(self):
        results = {
            "results": {"0": 10},
            "metadata": {"status": Constant.JOB_STATUS_COMPLETED},
        }

        returned = attach_fidelity_benchmark(results, {"00": 1.0})

        assert returned is results
        assert (
            "different bit widths"
            in results["metadata"]["benchmark"]["errors"]["fidelity"]
        )

    @patch("wy_qcos.engine.job_engine.simulate_qasm_probabilities")
    @patch("wy_qcos.engine.job_engine._run_code")
    def test_run_circuit_code_computes_fidelity_benchmark(
        self, mock_run_code, mock_simulate
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_wirecut.return_value = False
        mock_driver.get_wirecut_qubit_width.return_value = 2
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        job_id = "00000000-0000-4000-8000-000000000001"
        source_code = "OPENQASM 2.0; qreg q[2];"
        mock_transpiler.parse.return_value = {f"{job_id}-0": (2, None)}
        ideal_probabilities = {"00": 0.5, "11": 0.5}
        mock_simulate.return_value = ideal_probabilities
        mock_run_code.return_value = (
            {
                "results": {"00": 50, "11": 50},
                "metadata": {"status": Constant.JOB_STATUS_COMPLETED},
            },
            mock_driver,
            mock_transpiler,
            {},
        )
        job_info = {
            "data": {
                "job_id": job_id,
                "code_type": Constant.CODE_TYPE_QASM,
                "driver_options": {"compute_fidelity": True},
            }
        }

        results, _, _, _ = run_circuit_code(
            0,
            {f"{job_id}-0": source_code},
            job_info,
            mock_driver,
            mock_transpiler,
        )

        mock_simulate.assert_called_once_with(source_code)
        benchmark = results["metadata"]["benchmark"]
        assert benchmark["ideal_probabilities"] == (ideal_probabilities)
        assert benchmark["ideal_source"] == "qiskit_aer_sim"
        assert benchmark["metrics"]["squared_bhattacharyya"] == pytest.approx(
            1.0
        )

    @patch("wy_qcos.engine.job_engine.simulate_qasm_probabilities")
    @patch("wy_qcos.engine.job_engine._run_code")
    def test_run_circuit_code_keeps_results_when_ideal_simulation_fails(
        self, mock_run_code, mock_simulate
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_wirecut.return_value = False
        mock_driver.get_wirecut_qubit_width.return_value = 2
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        job_id = "00000000-0000-4000-8000-000000000001"
        source_code = "OPENQASM 2.0; qreg q[2];"
        mock_transpiler.parse.return_value = {f"{job_id}-0": (2, None)}
        mock_simulate.side_effect = ValueError("simulation unavailable")
        hardware_results = {"00": 40, "11": 60}
        mock_run_code.return_value = (
            {
                "results": hardware_results,
                "metadata": {"status": Constant.JOB_STATUS_COMPLETED},
            },
            mock_driver,
            mock_transpiler,
            {},
        )
        job_info = {
            "data": {
                "job_id": job_id,
                "code_type": Constant.CODE_TYPE_QASM,
                "driver_options": {"compute_fidelity": True},
            }
        }

        results, _, _, _ = run_circuit_code(
            0,
            {f"{job_id}-0": source_code},
            job_info,
            mock_driver,
            mock_transpiler,
        )

        assert results["results"] == hardware_results
        assert (
            "simulation unavailable"
            in results["metadata"]["benchmark"]["errors"]["ideal_simulation"]
        )

    @patch("wy_qcos.engine.job_engine.format_error_results")
    def test_run_circuit_code_exceeds_limit_no_wirecut(
        self, mock_format_error
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_wirecut.return_value = False
        mock_driver.get_wirecut_qubit_width.return_value = 1
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        mock_transpiler.parse.return_value = {
            "00000000-0000-4000-8000-000000000001-0": (20, None)
        }
        source_code_index = 0
        src_code_dict = {"00000000-0000-4000-8000-000000000001-0": "value"}
        job_info = {
            "data": {
                "job_id": "00000000-0000-4000-8000-000000000001",
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
        expected_error_result = {
            "results": None,
            "metadata": {"status": "FAILED", "error": "Qubit limit exceeded"},
        }
        mock_format_error.return_value = expected_error_result
        results, driver, transpiler, mapping = run_circuit_code(
            source_code_index,
            src_code_dict,
            job_info,
            mock_driver,
            mock_transpiler,
        )
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        assert mapping is None
        assert results == expected_error_result
        mock_format_error.assert_called_once()

    @patch(
        "wy_qcos.engine.job_engine."
        "generate_all_variant_subcircuits_for_execute"
    )
    @patch("wy_qcos.engine.job_engine._run_code")
    @patch(
        "wy_qcos.engine.job_engine."
        "reconstruct_probability_distribution_wire_cut"
    )
    def test_run_circuit_cutting_code_success(
        self, mock_reconstruct, mock_run_code, mock_generate_subs
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_wirecut.return_value = True
        mock_driver.get_wirecut_qubit_width.return_value = 2
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        mock_cut_wire = Mock()
        mock_cut_wire.num_cuts = 1
        mock_cut_wire.subcircuits_dict = {
            0: {f"variant-{i}": f"qasm-{i}" for i in range(3)},
            1: {f"variant-{i}": f"qasm-{i}" for i in range(3, 8)},
        }
        mock_generate_subs.return_value = (
            ["original-subcircuit1", "original-subcircuit2"],
            ["subcircuit1", "subcircuit2"],
            mock_cut_wire,
        )
        source_code_index = 0
        src_code_dict = {"00000000-0000-4000-8000-000000000001-0": "value"}
        job_info = {
            "data": {
                "job_id": "00000000-0000-4000-8000-000000000001",
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
        sub_results = [{"00": 0.6, "11": 0.4}, {"00": 0.3, "11": 0.7}]
        mock_run_code.return_value = (
            {"results": sub_results[0], "metadata": {"status": "COMPLETED"}},
            mock_driver,
            mock_transpiler,
            {},
        )
        reconstructed_probs = np.array([0.45, 0.0, 0.0, 0.55])
        mock_reconstruct.return_value = (reconstructed_probs, {})
        num_qubits = 2
        with (
            patch(
                "wy_qcos.engine.job_engine.time.perf_counter",
                side_effect=[10, 10.25, 20, 30, 31.5, 40, 42.25, 50],
            ),
            patch("wy_qcos.engine.job_engine.logger") as mock_logger,
        ):
            results, driver, transpiler, _ = run_circuit_cutting_code(
                source_code_index,
                src_code_dict,
                num_qubits,
                job_info,
                mock_driver,
                mock_transpiler,
            )
        assert results["num_qubits"] == 2
        assert "results" in results
        assert results["metadata"]["status"] == "COMPLETED"
        assert driver == mock_driver
        assert transpiler == mock_transpiler
        mock_generate_subs.assert_called_once()
        assert mock_run_code.call_count == 2
        mock_reconstruct.assert_called_once()
        log_messages = [
            call.args[0] for call in mock_logger.info.call_args_list
        ]
        assert any(
            "Wirecut subcircuits generated" in message
            and "original_count=2" in message
            and "variant_count=8" in message
            and "executable_count=2" in message
            and "duration_seconds=0.250000" in message
            for message in log_messages
        )
        assert any(
            "Wirecut subcircuit result received" in message
            and "subcircuit=1/2" in message
            and "duration_seconds=1.500000" in message
            for message in log_messages
        )
        assert any(
            "Wirecut subcircuit result received" in message
            and "subcircuit=2/2" in message
            and "duration_seconds=2.250000" in message
            for message in log_messages
        )
        assert any(
            "Wirecut subcircuit execution completed" in message
            and "executed_count=2" in message
            and "cache_hit_count=0" in message
            for message in log_messages
        )

    @patch("wy_qcos.engine.job_engine.SubcircuitResultCache.from_job_info")
    @patch(
        "wy_qcos.engine.job_engine."
        "generate_all_variant_subcircuits_for_execute"
    )
    @patch("wy_qcos.engine.job_engine._run_code")
    @patch(
        "wy_qcos.engine.job_engine."
        "reconstruct_probability_distribution_wire_cut"
    )
    def test_run_circuit_cutting_code_uses_cached_subcircuit_result(
        self,
        mock_reconstruct,
        mock_run_code,
        mock_generate_subs,
        mock_from_job_info,
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_wirecut_qubit_width.return_value = 2
        mock_transpiler = Mock()
        mock_generate_subs.return_value = (
            {},
            ["cached-subcircuit", "new-subcircuit"],
            Mock(),
        )
        result_cache = mock_from_job_info.return_value
        result_cache.get.side_effect = [{"00": 3, "11": 1}, None]
        executed_result = {"00": 1, "11": 3}
        mock_run_code.return_value = (
            {
                "results": executed_result,
                "metadata": {"status": "COMPLETED"},
            },
            mock_driver,
            mock_transpiler,
            {},
        )
        mock_reconstruct.return_value = (np.array([0.5, 0.0, 0.0, 0.5]), {})
        job_id = "00000000-0000-4000-8000-000000000001"
        job_info = {
            "data": {"job_id": job_id},
            "driver": {},
            "transpiler": {},
            "device": "test_device",
        }

        run_circuit_cutting_code(
            0,
            {f"{job_id}-0": "source"},
            2,
            job_info,
            mock_driver,
            mock_transpiler,
        )

        mock_run_code.assert_called_once()
        result_cache.set.assert_called_once_with(
            "new-subcircuit", job_info, executed_result
        )
        reconstructed_results = mock_reconstruct.call_args.args[1]
        np.testing.assert_array_equal(
            reconstructed_results[0], np.array([0.75, 0.0, 0.0, 0.25])
        )
        np.testing.assert_array_equal(
            reconstructed_results[1], np.array([0.25, 0.0, 0.0, 0.75])
        )

    @patch("wy_qcos.engine.job_engine.SubcircuitResultCache.from_job_info")
    @patch(
        "wy_qcos.engine.job_engine."
        "generate_all_variant_subcircuits_for_execute"
    )
    @patch("wy_qcos.engine.job_engine._run_code")
    @patch(
        "wy_qcos.engine.job_engine."
        "reconstruct_probability_distribution_wire_cut"
    )
    def test_run_circuit_cutting_code_all_results_cached(
        self,
        mock_reconstruct,
        mock_run_code,
        mock_generate_subs,
        mock_from_job_info,
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_wirecut_qubit_width.return_value = 2
        mock_generate_subs.return_value = ({}, ["subcircuit"], Mock())
        mock_from_job_info.return_value.get.return_value = {
            "00": 1,
            "11": 1,
        }
        mock_reconstruct.return_value = (np.array([0.5, 0.0, 0.0, 0.5]), {})
        job_id = "00000000-0000-4000-8000-000000000001"

        result, _, _, mapping = run_circuit_cutting_code(
            0,
            {f"{job_id}-0": "source"},
            2,
            {"data": {"job_id": job_id}},
            mock_driver,
            Mock(),
        )

        mock_run_code.assert_not_called()
        assert result["metadata"]["status"] == Constant.JOB_STATUS_COMPLETED
        assert result["results"] == {"00": 0.5, "11": 0.5}
        assert mapping is None

    @patch(
        "wy_qcos.engine.job_engine."
        "generate_all_variant_subcircuits_for_execute"
    )
    @patch("wy_qcos.engine.job_engine._run_code")
    def test_run_circuit_cutting_code_subcircuit_failed(
        self, mock_run_code, mock_generate_subs
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_wirecut.return_value = True
        mock_driver.get_wirecut_qubit_width.return_value = 4
        mock_driver.get_name.return_value = "TestDevice"
        mock_transpiler = Mock()
        mock_cut_wire = Mock()
        mock_generate_subs.return_value = (
            {},
            ["subcircuit1", "subcircuit2"],
            mock_cut_wire,
        )
        source_code_index = 0
        src_code_dict = {"00000000-0000-4000-8000-000000000001-0": "value"}
        job_info = {
            "data": {
                "job_id": "00000000-0000-4000-8000-000000000001",
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
        failed_result = {
            "results": None,
            "metadata": {"status": "FAILED", "error": "Subcircuit error"},
        }
        mock_run_code.return_value = (
            failed_result,
            mock_driver,
            mock_transpiler,
            {},
        )
        num_qubits = 2
        results, _, _, _ = run_circuit_cutting_code(
            source_code_index,
            src_code_dict,
            num_qubits,
            job_info,
            mock_driver,
            mock_transpiler,
        )
        assert results == failed_result
        mock_run_code.assert_called_once()

    @patch("wy_qcos.engine.job_engine.parse.submit")
    def test_flow_parse(self, mock_parse):
        mock_parse.return_value = Mock()
        result, _ = flow_parse(
            {},
            TranspilerBase(),
            Constant.CODE_TYPE_QASM2,
        )
        assert isinstance(result, Mock) is True

    @patch("wy_qcos.engine.job_engine.transpile.submit")
    def test_flow_transpile(self, mock_transpile):
        mock_transpile.return_value = Mock()
        result, _ = flow_transpile("", TranspilerBase(), DriverBase())
        assert isinstance(result, Mock) is True

    @patch("wy_qcos.engine.job_engine.task_monitor.submit")
    def test_flow_task_monitor(self, mock_task_monitor):
        mock_task_monitor.return_value = None
        assert flow_task_monitor("") is None

    @patch("wy_qcos.engine.job_engine.driver_run.submit")
    def test_flow_run_driver(self, mock_driver_run):
        mock_driver_run.return_value = Mock()
        result, _ = flow_run_driver({}, 6, DriverBase(), {})
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

    @patch("wy_qcos.engine.job_engine.update_progress")
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
        return_value = parse.fn([], TranspilerBase(), Constant.CODE_TYPE_QASM2)
        assert return_value["parsed_src_code"] is None

    def test_transpile(self):
        return_value = transpile.fn([], DriverBase, TranspilerBase())
        assert return_value["transpile_results"] is None

    def test_driver_run(self):
        return_value = driver_run.fn([], DriverBase, 5, self.job_data)
        assert return_value["results"] is None

    @patch("wy_qcos.engine.job_engine.init_logger")
    @patch("wy_qcos.engine.job_engine.register_signals")
    @patch("wy_qcos.engine.job_engine.flow_task_monitor")
    @patch("wy_qcos.engine.job_engine.run_code")
    def test_job_flow(
        self,
        mock_run_code,
        mock_flow_task_monitor,
        mock_register_signals,
        mock_init_logger,
    ):
        mock_run_code.return_value = (
            self.job_results,
            None,
            None,
            self.mapping_dict,
        )
        mock_init_logger.return_value = None
        mock_flow_task_monitor.return_value = None
        mock_register_signals.return_values = None
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
        self.job_info["data"]["backend"] = "dummy"
        self.job_info["data"]["job_enqueue_at"] = 1783045405.121
        self.job_info["data"]["job_schedule_started_at"] = 1783045402.076
        self.job_info["data"]["job_schedule_ended_at"] = 1783045407.121
        self.job_info["data"]["job_schedule_duration"] = 1
        self.job_info["global"] = {
            "configs": {
                "REDIS": {
                    "REDIS_SERVER_IP": "127.0.0.1",
                    "REDIS_SERVER_PORT": 6379,
                }
            }
        }
        self.job_info["device"] = {"configs": {}}
        job_results_list = raw_job_flow_func(self.job_info)
        assert len(job_results_list) == len(
            self.job_info["data"]["source_code"]
        )
        assert job_results_list[0] == self.job_results
        mock_run_code.assert_called_once()
        assert (
            self.src_code_info.aggregation_type
            == Constant.AGGREGATION_TYPE_NONE
        )

    @patch("wy_qcos.engine.job_engine.format_error_results")
    @patch("wy_qcos.engine.job_engine.init_driver.submit")
    def test_run_code_driver_init_error(
        self, mock_init_driver, mock_format_error
    ):
        mock_init_driver.return_value.result.return_value = {
            "driver": None,
            "error": ValueError("init failed"),
        }
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        results, driver, transpiler, mapping = run_code(
            0,
            {"job-0": "code"},
            {
                "data": {
                    "code_type": Constant.CODE_TYPE_QASM,
                    "driver_options": {},
                    "transpiler_options": None,
                },
                "driver": {"module_name": "m", "class_name": "C"},
                "transpiler": {"module_name": "m", "class_name": "T"},
                "device": {},
            },
            None,
            None,
            {"driver": None},
        )
        assert results["metadata"]["status"] == "FAILED"
        assert driver is None
        assert transpiler is None
        assert mapping is None

    @patch("wy_qcos.engine.job_engine.format_error_results")
    @patch("wy_qcos.engine.job_engine.init_transpiler.submit")
    def test_run_code_transpiler_init_error(
        self, mock_init_transpiler, mock_format_error
    ):
        mock_driver = Mock(spec=DriverBase)
        mock_driver.name = "Driver"
        mock_init_transpiler.return_value.result.return_value = {
            "transpiler": None,
            "error": ValueError("transpiler failed"),
        }
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        results, driver, transpiler, mapping = run_code(
            0,
            {"job-0": "code"},
            {
                "data": {
                    "code_type": Constant.CODE_TYPE_QASM,
                    "driver_options": {},
                    "transpiler_options": None,
                },
                "driver": {"module_name": "m", "class_name": "C"},
                "transpiler": {"module_name": "m", "class_name": "T"},
                "device": {},
            },
            mock_driver,
            None,
            {"driver": mock_driver},
        )
        assert results["metadata"]["status"] == "FAILED"
        assert driver == mock_driver
        assert transpiler is None
        assert mapping is None

    @patch("wy_qcos.engine.job_engine.format_error_results")
    @patch("wy_qcos.engine.job_engine.check_matrix")
    def test_run_qubo_code_check_matrix_error(
        self, mock_check_matrix, mock_format_error
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 5
        mock_driver.get_enable_subqubo.return_value = False
        mock_driver.get_enable_prec_reduce.return_value = True
        qubo_matrix = np.array([[1, 2], [2, 3]])
        job_id = "00000000-0000-4000-8000-000000000001"
        mock_check_matrix.return_value = (False, "bad matrix")
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        results, _, _, _ = run_qubo_code(
            0,
            {f"{job_id}-0": qubo_matrix},
            {"data": {"job_id": job_id}},
            mock_driver,
            Mock(),
        )
        assert results["metadata"]["status"] == "FAILED"

    @patch("wy_qcos.engine.job_engine.format_error_results")
    @patch("wy_qcos.engine.job_engine.check_matrix")
    @patch("wy_qcos.engine.job_engine.check_qubo_matrix_bit_width")
    def test_run_qubo_code_width_error_with_message(
        self,
        mock_check_width,
        mock_check_matrix,
        mock_format_error,
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 5
        mock_driver.get_enable_subqubo.return_value = False
        mock_driver.get_enable_prec_reduce.return_value = True
        qubo_matrix = np.array([[1, 2], [2, 3]])
        job_id = "00000000-0000-4000-8000-000000000001"
        mock_check_matrix.return_value = (True, "")
        mock_check_width.return_value = (False, "width error")
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        results, _, _, _ = run_qubo_code(
            0,
            {f"{job_id}-0": qubo_matrix},
            {"data": {"job_id": job_id}},
            mock_driver,
            Mock(),
        )
        assert results["metadata"]["status"] == "FAILED"

    @patch("wy_qcos.engine.job_engine.format_error_results")
    @patch("wy_qcos.engine.job_engine.check_matrix")
    @patch("wy_qcos.engine.job_engine.check_qubo_matrix_bit_width")
    def test_run_qubo_code_width_error_prec_reduce_disabled(
        self,
        mock_check_width,
        mock_check_matrix,
        mock_format_error,
    ):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 5
        mock_driver.get_enable_subqubo.return_value = False
        mock_driver.get_enable_prec_reduce.return_value = False
        qubo_matrix = np.array([[1, 2], [2, 3]])
        job_id = "00000000-0000-4000-8000-000000000001"
        mock_check_matrix.return_value = (True, "")
        mock_check_width.return_value = (False, "")
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        results, _, _, _ = run_qubo_code(
            0,
            {f"{job_id}-0": qubo_matrix},
            {"data": {"job_id": job_id}},
            mock_driver,
            Mock(),
        )
        assert results["metadata"]["status"] == "FAILED"

    @patch("wy_qcos.engine.job_engine.format_error_results")
    @patch("wy_qcos.engine.job_engine._run_code")
    def test_run_subqubo_code_size_below_threshold(
        self, mock_run_code, mock_format_error
    ):
        mock_driver = Mock()
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        results, _, _, _ = run_subqubo_code(
            4,
            100,
            0,
            {"00000000-0000-4000-8000-000000000001-0": np.array([[1]])},
            {"data": {"job_id": "00000000-0000-4000-8000-000000000001"}},
            mock_driver,
            Mock(),
        )
        assert results["metadata"]["status"] == "FAILED"
        mock_run_code.assert_not_called()

    @patch("wy_qcos.engine.job_engine.format_error_results")
    def test_run_circuit_code_compile_error(self, mock_format_error):
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        mock_driver.get_enable_wirecut.return_value = False
        mock_transpiler = Mock()
        mock_transpiler.parse.side_effect = Exception("compile failed")
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        results, _, _, mapping = run_circuit_code(
            0,
            {"00000000-0000-4000-8000-000000000001-0": "value"},
            {
                "data": {
                    "job_id": "00000000-0000-4000-8000-000000000001",
                    "code_type": Constant.CODE_TYPE_QASM,
                }
            },
            mock_driver,
            mock_transpiler,
        )
        assert results["metadata"]["status"] == "FAILED"
        assert mapping is None

    # --- Aggregation-related test cases ---

    def test_create_src_code_info_with_internal_aggregation(self):
        """Test create_src_code_info with internal aggregation type."""
        job_data = {
            "job_id": "00000000-0000-4000-8000-000000000001",
            "source_code": [self.simple_data, self.simple_data],
            "circuit_aggregation": Constant.AGGREGATION_TYPE_INTERNAL,
        }
        result = create_src_code_info(job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_INTERNAL
        assert len(result.src_code_list) == 1
        assert len(result.src_code_list[0]) == 2

    def test_create_src_code_info_with_external_aggregation(self):
        """Test create_src_code_info with external aggregation type."""
        job_data = {
            "job_id": "00000000-0000-4000-8000-000000000001",
            "source_code": [self.simple_data],
            "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
        }
        result = create_src_code_info(job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL
        assert len(result.src_code_list) == 1

    def test_create_src_code_info_exceeds_max_aggregation_jobs(self):
        """Test create_src_code_info when codes exceed MAX_AGGREGATION_JOBS.

        Note: Due to src_code_map.clear() clearing the same object
        reference already appended to the list, the first batch gets
        cleared and remaining items fill it. The skipped item at the
        boundary is lost (continue skips it without adding).
        Both list entries point to the same dict object.
        """
        num_codes = Constant.MAX_AGGREGATION_JOBS + 3
        job_data = {
            "job_id": "00000000-0000-4000-8000-000000000001",
            "source_code": [self.simple_data] * num_codes,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_INTERNAL,
        }
        result = create_src_code_info(job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_INTERNAL
        # Due to clear() on same reference, src_code_list has 2 entries
        # both pointing to the same dict with remaining items
        assert len(result.src_code_list) == 2
        # Items after the MAX_AGGREGATION_JOBS boundary (skipped one)
        # remain in the dict, and the dict is appended twice
        assert (
            len(result.src_code_list[0])
            == num_codes - Constant.MAX_AGGREGATION_JOBS - 1
        )

    def test_create_src_code_info_none_aggregation_multiple_codes(self):
        """Test create_src_code_info with None agg and multi source codes."""
        job_data = {
            "job_id": "00000000-0000-4000-8000-000000000001",
            "source_code": [self.simple_data, self.simple_data],
            "circuit_aggregation": None,
        }
        result = create_src_code_info(job_data)
        assert result.aggregation_type == Constant.AGGREGATION_TYPE_NONE
        # Each source code gets its own dict in separate list items
        assert len(result.src_code_list) == 2
        assert len(result.src_code_list[0]) == 1
        assert len(result.src_code_list[1]) == 1

    def test_update_src_code_info_with_sub_jobs(self):
        """Test update_src_code_info merges sub job source codes."""
        src_code_info = SourceCodeInfo()
        src_code_info.aggregation_type = Constant.AGGREGATION_TYPE_EXTERNAL
        src_code_info.src_code_list = [
            {"00000000-0000-4000-8000-000000000001-0": self.simple_data}
        ]
        src_code_info.sub_flow_list = []
        aggregation_info = MagicMock()
        aggregation_info.sub_jobs = {
            "00000000-0000-4000-8000-000000000002-0": {
                "job_info": {
                    "data": {
                        "source_code": ["sub_code_1"],
                        "flow_run_id": "flow-run-0002",
                    }
                }
            },
            "00000000-0000-4000-8000-000000000003-0": {
                "job_info": {
                    "data": {
                        "source_code": ["sub_code_2"],
                        "flow_run_id": "flow-run-0003",
                    }
                }
            },
        }
        result = update_src_code_info(src_code_info, aggregation_info)
        assert len(result.src_code_list) == 1
        # Original code + 2 sub job codes
        assert len(result.src_code_list[0]) == 3
        assert (
            "00000000-0000-4000-8000-000000000001-0" in result.src_code_list[0]
        )
        # update_src_code_info appends "-0" to the sub job key
        assert (
            "00000000-0000-4000-8000-000000000002-0-0"
            in result.src_code_list[0]
        )
        assert (
            "00000000-0000-4000-8000-000000000003-0-0"
            in result.src_code_list[0]
        )
        # sub_flow_list should contain flow run ids
        assert "flow-run-0002" in result.sub_flow_list
        assert "flow-run-0003" in result.sub_flow_list

    def test_update_src_code_info_empty_src_code_list(self):
        """Test update_src_code_info raises ValueError on empty list."""
        src_code_info = SourceCodeInfo()
        src_code_info.src_code_list = []
        with pytest.raises(ValueError, match="unexpected input"):
            update_src_code_info(src_code_info, MagicMock())

    def test_split_dict_basic(self):
        """Test split_dict splits keys by specified lengths."""
        orig_dict = {
            "0011": 100,
            "1100": 200,
        }
        split_len = [2, 2]
        result = split_dict(orig_dict, split_len)
        assert len(result) == 2
        assert result[0] == {"00": 100, "11": 200}
        assert result[1] == {"11": 100, "00": 200}

    def test_split_dict_unequal_lengths(self):
        """Test split_dict with unequal split lengths."""
        orig_dict = {
            "00101": 50,
            "11010": 150,
        }
        split_len = [2, 3]
        result = split_dict(orig_dict, split_len)
        assert len(result) == 2
        assert result[0] == {"00": 50, "11": 150}
        assert result[1] == {"101": 50, "010": 150}

    def test_get_internal_aggregated_results_metadata(self):
        """Test sets AGGREGATION_TYPE_INTERNAL in metadata."""
        job_results = {
            "results": {"0011": 500, "1100": 300},
            "metadata": {"ended_at": datetime.now()},
            "profiling": {},
        }
        mapping_dict = {
            "job-1-0": 2,
            "job-2-0": 2,
        }
        result = get_internal_aggregated_results(job_results, mapping_dict)
        assert len(result) == 2
        for item in result:
            assert (
                item["metadata"]["circuit_aggregation"]
                == Constant.AGGREGATION_TYPE_INTERNAL
            )

    def test_get_external_aggregated_results_metadata(self):
        """Test sets AGGREGATION_TYPE_EXTERNAL in sub_results metadata."""
        job_results = {
            "results": {"0011": 500, "1100": 300},
            "metadata": {"ended_at": datetime.now()},
            "profiling": {},
        }
        mapping_dict = {
            "job-1-0": 2,
            "job-2-0": 2,
        }
        result = get_external_aggregated_results(job_results, mapping_dict)
        # parent job results kept
        assert result["results"] is not None
        assert result["num_qubits"] == 2
        # sub_results should contain 1 entry (second mapping)
        assert len(result["sub_results"]) == 1
        for sub_id, sub_res in result["sub_results"].items():
            assert (
                sub_res["metadata"]["circuit_aggregation"]
                == Constant.AGGREGATION_TYPE_EXTERNAL
            )

    def test_get_internal_aggregated_results_none_mapping_dict(self):
        """Test  raises ValueError when mapping_dict is None."""
        job_results = {"results": {"00": 1}, "metadata": {}}
        with pytest.raises(ValueError, match="mapping_dict is none"):
            get_internal_aggregated_results(job_results, None)

    def test_get_external_aggregated_results_none_mapping_dict(self):
        """Test raises ValueError when mapping_dict is None."""
        job_results = {"results": {"00": 1}, "metadata": {}}
        with pytest.raises(ValueError, match="mapping_dict is none"):
            get_external_aggregated_results(job_results, None)

    def test_get_external_aggregated_results_single_mapping(self):
        """Test  with a single mapping entry in mapping_dict."""
        job_results = {
            "results": {"00": 500, "01": 300},
            "metadata": {"ended_at": datetime.now()},
            "profiling": {},
        }
        mapping_dict = {
            "job-1-0": 2,
        }
        result = get_external_aggregated_results(job_results, mapping_dict)
        # Single mapping: parent keeps results, no sub_results
        assert result["results"] == {"00": 500, "01": 300}
        assert result["num_qubits"] == 2
        assert (
            result.get("sub_results") is None
            or len(result["sub_results"]) == 0
        )

    @patch("wy_qcos.engine.job_engine.update_progress")
    def test_task_monitor_with_agg_sub_job_list(self, mock_update_progress):
        """Test task_monitor updates progress for agg sub jobs."""
        mock_update_progress.return_value = None
        mock_driver = Mock()
        mock_driver.get_progress.return_value = 50
        monitor_info = {
            "running": False,
            "driver": mock_driver,
            "progress": 30,
            "source_code_count": 2,
            "job_id": "parent-job-id",
            "db_engine": Mock(),
            "agg_sub_job_list": ["sub-job-1", "sub-job-2"],
        }
        task_monitor.fn(monitor_info)
        # When running=False, it should set progress to 100
        # for both parent and sub jobs
        assert mock_update_progress.call_count >= 3

    @patch("wy_qcos.engine.job_engine.init_logger")
    @patch("wy_qcos.engine.job_engine.register_signals")
    @patch("wy_qcos.engine.job_engine.flow_task_monitor")
    @patch("wy_qcos.engine.job_engine.run_code")
    def test_job_flow_with_internal_aggregation(
        self,
        mock_run_code,
        mock_flow_task_monitor,
        mock_register_signals,
        mock_init_logger,
    ):
        """Test job_flow with internal aggregation type."""
        internal_mapping_dict = {
            "00000000-0000-4000-8000-000000000001-0": 1,
            "00000000-0000-4000-8000-000000000001-1": 1,
        }
        internal_job_results = {
            "results": {"00": 500, "11": 500},
            "metadata": {"ended_at": datetime.now()},
            "profiling": {},
        }
        mock_run_code.return_value = (
            internal_job_results,
            None,
            None,
            internal_mapping_dict,
        )
        mock_init_logger.return_value = None
        mock_flow_task_monitor.return_value = None
        mock_register_signals.return_values = None
        raw_job_flow_func = job_flow.__wrapped__
        job_info = {
            "data": {
                "job_id": "00000000-0000-4000-8000-000000000001",
                "source_code": [self.simple_data, self.simple_data],
                "circuit_aggregation": Constant.AGGREGATION_TYPE_INTERNAL,
                "code_type": Constant.CODE_TYPE_QASM,
                "driver_options": {},
                "backend": "dummy",
                "job_enqueue_at": 1783045405.121,
                "job_schedule_started_at": 1783045402.076,
                "job_schedule_ended_at": 1783045407.121,
                "job_schedule_duration": 0,
                "profiling": [
                    Constant.PROFILING_TYPE_CODE,
                    Constant.PROFILING_TYPE_SCHEDULING,
                ],
            },
            "driver": {
                "module_name": "wy_qcos.driver.dummy.driver_dummy",
                "class_name": "DriverDummy",
            },
            "transpiler": {
                "module_name": "wy_qcos.transpiler.cmss.transpiler_cmss",
                "class_name": "TranspilerCmss",
            },
            "global": {
                "configs": {
                    "REDIS": {
                        "REDIS_SERVER_IP": "127.0.0.1",
                        "REDIS_SERVER_PORT": 6379,
                    }
                }
            },
            "device": {"configs": {}},
        }
        job_results_list = raw_job_flow_func(job_info)
        # Internal aggregation should produce extended results
        assert isinstance(job_results_list, list)
        mock_run_code.assert_called_once()

    def test_get_src_code_cnt_multiple_dicts(self):
        """Test get_src_code_cnt with multiple dicts in src_code_list."""
        src_code_info = SourceCodeInfo()
        src_code_info.src_code_list = [
            {"key1": "val1", "key2": "val2"},
            {"key3": "val3"},
        ]
        result = get_src_code_cnt(src_code_info)
        assert result == 3

    def test_get_src_code_cnt_empty_list(self):
        """Test get_src_code_cnt with empty src_code_list."""
        src_code_info = SourceCodeInfo()
        src_code_info.src_code_list = []
        result = get_src_code_cnt(src_code_info)
        assert result == 0

    @patch("wy_qcos.engine.job_engine.format_error_results")
    @patch(
        "wy_qcos.engine.job_engine."
        "generate_all_variant_subcircuits_for_execute"
    )
    def test_run_circuit_cutting_code_generate_error(
        self, mock_generate, mock_format_error
    ):
        mock_generate.side_effect = Exception("generate failed")
        mock_format_error.return_value = {"metadata": {"status": "FAILED"}}
        mock_driver = Mock()
        mock_driver.get_max_qubits.return_value = 2
        results, _, _, mapping = run_circuit_cutting_code(
            0,
            {"00000000-0000-4000-8000-000000000001-0": "value"},
            10,
            {
                "data": {
                    "job_id": "00000000-0000-4000-8000-000000000001",
                    "code_type": Constant.CODE_TYPE_QASM,
                }
            },
            mock_driver,
            Mock(),
        )
        assert results["metadata"]["status"] == "FAILED"
        assert mapping is None
