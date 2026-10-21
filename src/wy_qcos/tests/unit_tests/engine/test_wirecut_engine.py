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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import json

import pytest
from unittest.mock import MagicMock, patch

from wy_qcos.common.constant import Constant
from wy_qcos.engine.wirecut_engine import (
    _build_subqubo_schedule_entries,
    _extract_subqubo_solution,
    _get_device_max_qubits,
    poll_job_results,
    submit_jobs,
    wirecut_schedule,
)


def _redis_key(job_id, flow_run_id):
    """Build the redis key (also the pub/sub channel) of a sub-job."""
    return f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}"


def _message(channel, record):
    """Build a pub/sub message dict as delivered by redis."""
    return {
        "type": "message",
        "channel": channel,
        "data": json.dumps(record),
    }


def _record(status, progress=None):
    """Build a minimal sub-job redis record."""
    record = {"job_status": status}
    if progress is not None:
        record["progress"] = progress
    return record


def _client(get_side_effects=None, messages=None):
    """Build a mocked redis client with a mocked pubsub object.

    Args:
            get_side_effects: list used as the redis client ``get``
    ui            side effect (consumed by successive snapshot reads,
                one entry per sub-job per round).
            messages: list of values returned by ``get_message`` in
                order (message dicts or None).
    """
    client = MagicMock()
    if get_side_effects is not None:
        client.get.side_effect = get_side_effects
    if messages is not None:
        pubsub = client.pubsub.return_value
        pubsub.get_message.side_effect = list(messages)
    return client


class TestPollJobResults:
    """Unit tests for wirecut_engine.poll_job_results."""

    def test_no_redis_client_returns_empty(self):
        with patch(
            "wy_qcos.engine.wirecut_engine.get_redis_client",
            return_value=None,
        ):
            results = poll_job_results(
                [{"job_id": "job-1", "flow_run_id": "f1"}],
                redis_instance=None,
            )
        assert results == []

    def test_empty_job_list_returns_empty(self):
        client = _client()
        results = poll_job_results([], job_id="job-1", redis_instance=client)
        assert results == []
        client.pubsub.assert_not_called()

    def test_already_terminal_collected_from_snapshot(self):
        # Simulates the race the fix targets: the sub-job reached
        # terminal status before poll_job_results subscribed, so no
        # pub/sub message will ever arrive. The snapshot read-back
        # must collect it instead.
        job_id = "job-1"
        key = _redis_key(job_id, "f1")
        record = _record(Constant.JOB_STATUS_COMPLETED, progress=100)
        client = _client(get_side_effects=[json.dumps(record)])
        monitor_info = {"sub_job_progress": {}}

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            job_id=job_id,
            redis_instance=client,
            monitor_info=monitor_info,
        )

        assert results == [record]
        pubsub = client.pubsub.return_value
        pubsub.subscribe.assert_called_once_with(key)
        # the subscription loop is skipped entirely
        pubsub.get_message.assert_not_called()
        pubsub.unsubscribe.assert_called_once()
        pubsub.close.assert_called_once()
        client.delete.assert_called_once_with(key)
        assert monitor_info["sub_job_progress"] == {"f1": 100}

    def test_subscribe_issued_before_snapshot_read(self):
        # SUBSCRIBE must be issued before the snapshot GET so that
        # no publication can fall in between the two operations.
        job_id = "job-1"
        record = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(get_side_effects=[json.dumps(record)])

        poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
        )

        names = [c[0] for c in client.mock_calls]
        assert names.index("pubsub().subscribe") < names.index("get")

    def test_non_terminal_snapshot_waits_for_message(self):
        # A RUNNING record in the snapshot must not be collected;
        # the sub-job completes later via its pub/sub notification.
        job_id = "job-1"
        key = _redis_key(job_id, "f1")
        running = _record(Constant.JOB_STATUS_RUNNING, progress=50)
        terminal = _record(Constant.JOB_STATUS_COMPLETED, progress=100)
        client = _client(
            get_side_effects=[json.dumps(running)],
            messages=[
                _message(
                    key,
                    _record(Constant.JOB_STATUS_RUNNING, progress=75),
                ),
                _message(key, terminal),
            ],
        )

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
        )

        assert results == [terminal]

    def test_mixed_snapshot_and_pubsub(self):
        # Sub-job fa is already terminal in redis while fb completes
        # later via pub/sub; both must be collected.
        job_id = "job-1"
        key_a = _redis_key(job_id, "fa")
        key_b = _redis_key(job_id, "fb")
        terminal_a = _record(Constant.JOB_STATUS_COMPLETED, progress=100)
        running_b = _record(Constant.JOB_STATUS_RUNNING, progress=40)
        terminal_b = _record(Constant.JOB_STATUS_COMPLETED, progress=100)
        client = _client(
            get_side_effects=[
                json.dumps(terminal_a),
                json.dumps(running_b),
            ],
            messages=[_message(key_b, terminal_b)],
        )
        monitor_info = {"sub_job_progress": {}}

        results = poll_job_results(
            [
                {"job_id": job_id, "flow_run_id": "fa"},
                {"job_id": job_id, "flow_run_id": "fb"},
            ],
            redis_instance=client,
            monitor_info=monitor_info,
        )

        assert results == [terminal_a, terminal_b]
        client.delete.assert_any_call(key_a)
        client.delete.assert_any_call(key_b)
        assert monitor_info["sub_job_progress"] == {"fa": 100, "fb": 100}

    def test_results_follow_new_job_list_order(self):
        # Sub-job fb completes first, fa later; the results list must
        # still follow the new_job_list order [fb, fa].
        job_id = "job-1"
        key_a = _redis_key(job_id, "fa")
        key_b = _redis_key(job_id, "fb")
        running = _record(Constant.JOB_STATUS_RUNNING, progress=10)
        terminal_a = _record(Constant.JOB_STATUS_COMPLETED)
        terminal_b = _record(Constant.JOB_STATUS_FAILED)
        client = _client(
            get_side_effects=[json.dumps(running), json.dumps(running)],
            messages=[
                _message(key_b, terminal_b),
                _message(key_a, terminal_a),
            ],
        )

        results = poll_job_results(
            [
                {"job_id": job_id, "flow_run_id": "fb"},
                {"job_id": job_id, "flow_run_id": "fa"},
            ],
            redis_instance=client,
        )

        assert results == [terminal_b, terminal_a]

    def test_snapshot_read_failure_tolerated(self):
        # A failing snapshot read must not abort polling; the
        # sub-job is still collected via its pub/sub notification.
        job_id = "job-1"
        key_a = _redis_key(job_id, "fa")
        terminal_a = _record(Constant.JOB_STATUS_COMPLETED)
        terminal_b = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(
            get_side_effects=[
                Exception("redis read failed"),
                json.dumps(terminal_b),
            ],
            messages=[_message(key_a, terminal_a)],
        )

        results = poll_job_results(
            [
                {"job_id": job_id, "flow_run_id": "fa"},
                {"job_id": job_id, "flow_run_id": "fb"},
            ],
            redis_instance=client,
        )

        assert results == [terminal_a, terminal_b]

    def test_lost_notification_recovered_by_timeout_snapshot(self):
        # Covers the real-world failure mode: the sub-job stores its
        # terminal record in redis (SET succeeds) but the pub/sub
        # notification is lost (PUBLISH lost). get_message times out
        # (returns None); the timeout snapshot must then collect the
        # terminal record from redis so the parent never hangs.
        job_id = "job-1"
        _redis_key(job_id, "f1")
        running = _record(Constant.JOB_STATUS_RUNNING, progress=50)
        terminal = _record(Constant.JOB_STATUS_COMPLETED, progress=100)
        client = _client(
            # round 1 (post-subscribe snapshot): still RUNNING;
            # round 2 (timeout snapshot): terminal record present
            get_side_effects=[
                json.dumps(running),
                json.dumps(terminal),
            ],
            messages=[None],
        )

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
        )

        assert results == [terminal]
        # the message loop timed out once before the fallback fired
        pubsub = client.pubsub.return_value
        assert pubsub.get_message.call_count == 1

    def test_timeout_snapshot_no_record_keeps_waiting(self):
        # A timeout with no terminal record yet must keep waiting
        # for the pub/sub notification instead of returning early.
        job_id = "job-1"
        key = _redis_key(job_id, "f1")
        terminal = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(
            get_side_effects=[None, None, json.dumps(terminal)],
            messages=[None, _message(key, terminal)],
        )

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
        )

        assert results == [terminal]

    def test_malformed_snapshot_record_skipped(self):
        # A malformed record in redis must be skipped without
        # aborting polling.
        job_id = "job-1"
        key_a = _redis_key(job_id, "fa")
        terminal_a = _record(Constant.JOB_STATUS_COMPLETED)
        terminal_b = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(
            get_side_effects=["not-a-json", json.dumps(terminal_b)],
            messages=[_message(key_a, terminal_a)],
        )

        results = poll_job_results(
            [
                {"job_id": job_id, "flow_run_id": "fa"},
                {"job_id": job_id, "flow_run_id": "fb"},
            ],
            redis_instance=client,
        )

        assert results == [terminal_a, terminal_b]

    def test_missing_snapshot_key_tolerated(self):
        # A sub-job with no redis record yet (get returns None) must
        # still be collected later via pub/sub.
        job_id = "job-1"
        key_a = _redis_key(job_id, "fa")
        terminal_a = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(
            get_side_effects=[None],
            messages=[_message(key_a, terminal_a)],
        )

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "fa"}],
            redis_instance=client,
        )

        assert results == [terminal_a]

    def test_unknown_channel_message_ignored(self):
        # Messages on channels that match no pending sub-job are
        # ignored.
        job_id = "job-1"
        key = _redis_key(job_id, "f1")
        running = _record(Constant.JOB_STATUS_RUNNING)
        terminal = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(
            get_side_effects=[json.dumps(running)],
            messages=[
                _message(_redis_key(job_id, "unknown"), terminal),
                _message(key, terminal),
            ],
        )

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
        )

        assert results == [terminal]

    def test_non_message_and_malformed_messages_skipped(self):
        # Subscribe confirmations, None returns (message timeout
        # triggering the redis read-back fallback) and malformed
        # payloads must all be skipped without aborting the loop.
        # The None entry triggers a second snapshot round, so the
        # redis get side effect provides two RUNNING records.
        job_id = "job-1"
        key = _redis_key(job_id, "f1")
        running = _record(Constant.JOB_STATUS_RUNNING)
        terminal = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(
            get_side_effects=[json.dumps(running), json.dumps(running)],
            messages=[
                None,
                {"type": "subscribe", "channel": key, "data": 1},
                {"type": "message", "channel": key, "data": "not-json"},
                _message(key, terminal),
            ],
        )

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
        )

        assert results == [terminal]

    def test_bytes_channel_and_data_decoded(self):
        # Channels and payloads delivered as bytes must be decoded.
        job_id = "job-1"
        key = _redis_key(job_id, "f1")
        running = _record(Constant.JOB_STATUS_RUNNING)
        terminal = _record(Constant.JOB_STATUS_COMPLETED, progress=100)
        client = _client(
            get_side_effects=[json.dumps(running)],
            messages=[
                {
                    "type": "message",
                    "channel": key.encode("utf-8"),
                    "data": json.dumps(terminal).encode("utf-8"),
                }
            ],
        )

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
        )

        assert results == [terminal]

    def test_monitor_info_optional(self):
        # monitor_info=None must not crash and results are still
        # collected from the snapshot.
        job_id = "job-1"
        terminal = _record(Constant.JOB_STATUS_COMPLETED)
        client = _client(get_side_effects=[json.dumps(terminal)])

        results = poll_job_results(
            [{"job_id": job_id, "flow_run_id": "f1"}],
            redis_instance=client,
            monitor_info=None,
        )

        assert results == [terminal]

    def test_progress_updated_from_snapshot_and_messages(self):
        # Progress from the snapshot and from pub/sub notifications
        # is written into monitor_info["sub_job_progress"].
        job_id = "job-1"
        key_b = _redis_key(job_id, "fb")
        terminal_a = _record(Constant.JOB_STATUS_COMPLETED, progress=80)
        client = _client(
            get_side_effects=[
                json.dumps(terminal_a),
                json.dumps(_record(Constant.JOB_STATUS_RUNNING)),
            ],
            messages=[
                _message(
                    key_b,
                    _record(Constant.JOB_STATUS_RUNNING, progress=30),
                ),
                _message(
                    key_b,
                    _record(Constant.JOB_STATUS_COMPLETED, progress=90),
                ),
            ],
        )
        monitor_info = {"sub_job_progress": {}}

        results = poll_job_results(
            [
                {"job_id": job_id, "flow_run_id": "fa"},
                {"job_id": job_id, "flow_run_id": "fb"},
            ],
            redis_instance=client,
            monitor_info=monitor_info,
        )

        assert len(results) == 2
        assert monitor_info["sub_job_progress"] == {"fa": 80, "fb": 90}


class TestWirecutSchedule:
    """Unit tests for wirecut_engine.wirecut_schedule."""

    @staticmethod
    def _device(name):
        return {
            "name": name,
            "driver_name": "dummy",
            "driver_module_name": "wy_qcos.driver.dummy.driver_dummy",
            "driver_class_name": "DriverDummy",
            "driver_package_paths": ["/some/path"],
            "configs": {"key": "value"},
        }

    def test_one_entry_per_device(self):
        devices = [self._device("dev-1"), self._device("dev-2")]

        results = wirecut_schedule({"source_codes": []}, devices)

        assert len(results) == 2
        for device, entry in zip(devices, results):
            assert entry["device_name"] == device["name"]
            assert entry["driver_name"] == device["driver_name"]
            assert entry["driver_module_name"] == device["driver_module_name"]
            assert entry["driver_class_name"] == device["driver_class_name"]
            assert (
                entry["driver_package_paths"] == device["driver_package_paths"]
            )
            assert entry["configs"] == device["configs"]
            assert len(entry["source_codes"]) == 1
            assert "OPENQASM 2.0" in entry["source_codes"][0]

    def test_no_devices_returns_empty(self):
        assert wirecut_schedule({"source_codes": []}, []) == []


class TestGetDeviceMaxQubits:
    """Unit tests for _get_device_max_qubits."""

    def test_top_level_max_qubits(self):
        device = {"name": "dev-1", "max_qubits": 100}
        assert _get_device_max_qubits(device) == 100

    def test_configs_max_qubits(self):
        device = {
            "name": "dev-1",
            "configs": {"max_qubits": 550},
        }
        assert _get_device_max_qubits(device) == 550

    def test_available_qubits_fallback(self):
        device = {"name": "dev-1", "available_qubits": 20}
        assert _get_device_max_qubits(device) == 20

    def test_returns_zero_when_missing(self):
        device = {"name": "dev-1"}
        assert _get_device_max_qubits(device) == 0

    def test_top_level_takes_priority(self):
        device = {
            "max_qubits": 100,
            "configs": {"max_qubits": 550},
            "available_qubits": 20,
        }
        assert _get_device_max_qubits(device) == 100

    def test_configs_takes_priority_over_available(self):
        device = {
            "configs": {"max_qubits": 550},
            "available_qubits": 20,
        }
        assert _get_device_max_qubits(device) == 550

    def test_string_value_converted_to_int(self):
        device = {"max_qubits": "100"}
        assert _get_device_max_qubits(device) == 100


class TestExtractSubquboSolution:
    """Unit tests for _extract_subqubo_solution."""

    def test_standard_path(self):
        record = {
            "results": [
                {
                    "results": {
                        "out_data": [
                            {"solutionVector": [1, 0, 1, 0]},
                        ],
                    },
                },
            ],
        }
        assert _extract_subqubo_solution(record) == [1, 0, 1, 0]

    def test_flattened_out_data_path(self):
        record = {
            "results": [
                {
                    "out_data": [
                        {"solutionVector": [-1, 1, -1]},
                    ],
                },
            ],
        }
        assert _extract_subqubo_solution(record) == [-1, 1, -1]

    def test_results_as_dict(self):
        record = {
            "results": {
                "out_data": [
                    {"solutionVector": [0, 1]},
                ],
            },
        }
        assert _extract_subqubo_solution(record) == [0, 1]

    def test_empty_record(self):
        assert _extract_subqubo_solution({}) == []

    def test_none_record(self):
        assert _extract_subqubo_solution(None) == []

    def test_no_results_key(self):
        assert _extract_subqubo_solution({"job_status": "FAILED"}) == []

    def test_results_empty_list(self):
        assert _extract_subqubo_solution({"results": []}) == []

    def test_no_out_data(self):
        record = {"results": [{"results": {}}]}
        assert _extract_subqubo_solution(record) == []

    def test_empty_solution_vector(self):
        record = {
            "results": [
                {
                    "results": {
                        "out_data": [{"solutionVector": []}],
                    },
                },
            ],
        }
        assert _extract_subqubo_solution(record) == []

    def test_non_dict_result_skipped(self):
        record = {
            "results": [
                "not-a-dict",
                {
                    "results": {
                        "out_data": [{"solutionVector": [1]}],
                    },
                },
            ],
        }
        assert _extract_subqubo_solution(record) == [1]


class TestBuildSubquboScheduleEntries:
    """Unit tests for _build_subqubo_schedule_entries."""

    @staticmethod
    def _device(name):
        return {
            "name": name,
            "driver_name": f"Driver{name}",
            "driver_module_name": f"wy_qcos.driver.{name}",
            "driver_class_name": f"Driver{name}",
            "driver_package_paths": ["/path"],
            "configs": {"key": "val"},
        }

    @staticmethod
    def _task(matrix):
        return {"matrix": matrix}

    def test_round_robin_two_devices_three_tasks(self):
        devices = [self._device("d1"), self._device("d2")]
        tasks = [self._task([[1]]), self._task([[2]]), self._task([[3]])]
        results = _build_subqubo_schedule_entries(tasks, devices)
        assert len(results) == 3
        assert results[0]["device_name"] == "d1"
        assert results[1]["device_name"] == "d2"
        assert results[2]["device_name"] == "d1"
        assert results[0]["source_codes"] == [[[1]]]
        assert results[2]["source_codes"] == [[[3]]]

    def test_one_device_multiple_tasks(self):
        devices = [self._device("d1")]
        tasks = [self._task([[1]]), self._task([[2]])]
        results = _build_subqubo_schedule_entries(tasks, devices)
        assert len(results) == 2
        assert all(r["device_name"] == "d1" for r in results)

    def test_entry_shape(self):
        devices = [self._device("d1")]
        tasks = [self._task([[1]])]
        results = _build_subqubo_schedule_entries(tasks, devices)
        entry = results[0]
        assert set(entry.keys()) == {
            "device_name",
            "driver_name",
            "driver_module_name",
            "driver_class_name",
            "driver_package_paths",
            "configs",
            "source_codes",
        }

    def test_empty_tasks(self):
        devices = [self._device("d1")]
        assert _build_subqubo_schedule_entries([], devices) == []


class TestSubmitJobsSubJobId:
    """Unit tests for submit_jobs sub_job_id uniqueness."""

    @staticmethod
    def _schedule_entry(name):
        return {
            "device_name": name,
            "driver_name": "DriverDummy",
            "driver_module_name": "wy_qcos.driver.dummy",
            "driver_class_name": "DriverDummy",
            "driver_package_paths": [],
            "configs": {},
            "source_codes": [[[1]]],
        }

    def _job_info(self, job_id):
        return {
            "data": {
                "job_id": job_id,
                "options": {},
                "source_code": [],
                "code_type": "qubo",
            },
            "global": {"deployments": {}},
        }

    def test_sub_job_ids_are_unique_per_device(self):
        entries = [self._schedule_entry("d1"), self._schedule_entry("d2")]
        deployments = {
            "dev|d1": {"deploy_id": "id-1"},
            "dev|d2": {"deploy_id": "id-2"},
        }
        job_info = self._job_info("base-job")
        mock_client = MagicMock()
        mock_flow_run = MagicMock()
        mock_flow_run.id = "flow-1"
        mock_client.create_flow_run_from_deployment.return_value = (
            mock_flow_run
        )
        result = submit_jobs(
            entries,
            job_info,
            monitor_info={"sub_job_progress": {}},
            sync_client=mock_client,
            source_code_count=1,
            deployments=deployments,
        )
        job_ids = [job["job_id"] for job in result]
        assert len(set(job_ids)) == len(job_ids)
        assert "base-job_0" in job_ids
        assert "base-job_1" in job_ids

    def test_deployment_not_found_raises(self):
        entries = [self._schedule_entry("d1")]
        job_info = self._job_info("base-job")
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="not found"):
            submit_jobs(
                entries,
                job_info,
                monitor_info={"sub_job_progress": {}},
                sync_client=mock_client,
                source_code_count=1,
                deployments={},
            )
