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

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc.flavor import (
    create_flavor,
    delete_flavors,
    get_flavor,
    get_flavors,
    update_flavor,
)
from wy_qcos.common.constant import Constant
from wy_qcos.db.models import Flavor
from wy_qcos.flavor.errors import FlavorNotFoundError
from wy_qcos.flavor.flavor_manager import (
    DEFAULT_FLAVORS,
    EXTRA_PROPERTIES_ALLOWED_FIELDS,
    FlavorManager,
)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def make_flavor(
    flavor_id=None,
    name="test-flavor",
    project_id=None,
    description="desc",
    is_public=True,
    min_qubits=1,
    max_qubits=32,
    gate_fidelity_1q_min=None,
    gate_fidelity_2q_min=None,
    extra_properties=None,
):
    """Build a Flavor-like SimpleNamespace for testing."""
    if flavor_id is None:
        flavor_id = str(uuid.uuid4())
    if project_id is None:
        project_id = Constant.ADMIN_PROJECT_ID
    return SimpleNamespace(
        id=flavor_id,
        project_id=project_id,
        name=name,
        description=description,
        is_public=is_public,
        min_qubits=min_qubits,
        max_qubits=max_qubits,
        gate_fidelity_1q_min=gate_fidelity_1q_min,
        gate_fidelity_2q_min=gate_fidelity_2q_min,
        extra_properties=extra_properties,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_flavor_manager():
    """Build a FlavorManager with a mocked db_engine."""
    mock_engine = MagicMock()
    with patch.object(FlavorManager, "init_db") as mock_init:
        mgr = FlavorManager(mock_engine)
        mock_init.assert_called_once()
    mgr._db_engine = mock_engine
    return mgr


# ------------------------------------------------------------------ #
# FlavorManager.validate_extra_properties
# ------------------------------------------------------------------ #
class TestValidateExtraProperties:
    """Tests for FlavorManager.validate_extra_properties."""

    def test_none_returns_success(self):
        mgr = make_flavor_manager()
        ok, err = mgr.validate_extra_properties(None)
        assert ok is True
        assert err is None

    def test_empty_dict_returns_success(self):
        mgr = make_flavor_manager()
        ok, err = mgr.validate_extra_properties({})
        assert ok is True
        assert err is None

    def test_valid_key_returns_success(self):
        mgr = make_flavor_manager()
        ok, err = mgr.validate_extra_properties({
            "qc:devices": "dummy,qutip_sim"
        })
        assert ok is True
        assert err is None

    def test_invalid_format_no_colon(self):
        mgr = make_flavor_manager()
        ok, err = mgr.validate_extra_properties({"invalidkey": "value"})
        assert ok is False
        assert "Unsupported" in err

    def test_unsupported_field(self):
        mgr = make_flavor_manager()
        ok, err = mgr.validate_extra_properties({"qc:unsupported": "value"})
        assert ok is False
        assert "Unsupported" in err

    def test_allowed_fields_constant(self):
        assert "qc:devices" in (EXTRA_PROPERTIES_ALLOWED_FIELDS)


# ------------------------------------------------------------------ #
# FlavorManager.get_flavor / get_flavor_by_name / get_flavor_specs
# ------------------------------------------------------------------ #
class TestFlavorManagerGet:
    """Tests for FlavorManager get methods."""

    def test_get_flavor_empty_id(self):
        mgr = make_flavor_manager()
        assert mgr.get_flavor("") is None

    def test_get_flavor_by_name_empty(self):
        mgr = make_flavor_manager()
        assert mgr.get_flavor_by_name("") is None

    def test_get_flavor_specs_empty_id(self):
        mgr = make_flavor_manager()
        assert mgr.get_flavor_specs("") == {}

    def test_get_flavor_found(self):
        mgr = make_flavor_manager()
        flavor = make_flavor(extra_properties={"qc:devices": "dummy"})
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavor_by_uuid.return_value = (
                True,
                None,
                flavor,
            )
            result = mgr.get_flavor(flavor.id)
            assert result is flavor

    def test_get_flavor_not_found(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavor_by_uuid.return_value = (
                True,
                None,
                None,
            )
            assert mgr.get_flavor("nonexistent-id") is None

    def test_get_flavor_repo_error(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavor_by_uuid.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_flavor("some-id") is None

    def test_get_flavor_by_name_found(self):
        mgr = make_flavor_manager()
        flavor = make_flavor(name="g1.all")
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavor_by_name.return_value = (
                True,
                None,
                flavor,
            )
            assert mgr.get_flavor_by_name("g1.all") is flavor

    def test_get_flavor_by_name_not_found(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavor_by_name.return_value = (
                True,
                None,
                None,
            )
            assert mgr.get_flavor_by_name("missing") is None

    def test_get_flavor_by_name_repo_error(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavor_by_name.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_flavor_by_name("err") is None

    def test_get_flavor_specs_raises_when_not_found(self):
        mgr = make_flavor_manager()
        with patch.object(mgr, "get_flavor", return_value=None):
            with pytest.raises(FlavorNotFoundError):
                mgr.get_flavor_specs("missing-id")

    def test_get_flavor_specs_builds_full_dict(self):
        mgr = make_flavor_manager()
        flavor = make_flavor(
            min_qubits=2,
            max_qubits=10,
            gate_fidelity_1q_min=0.99,
            gate_fidelity_2q_min=0.995,
            extra_properties={"qc:devices": "dummy"},
        )
        with patch.object(mgr, "get_flavor", return_value=flavor):
            specs = mgr.get_flavor_specs(flavor.id)
        assert specs["min_qubits"] == 2
        assert specs["max_qubits"] == 10
        assert specs["gate_fidelity_1q_min"] == 0.99
        assert specs["gate_fidelity_2q_min"] == 0.995
        assert specs["qc:devices"] == "dummy"

    def test_get_flavor_specs_partial(self):
        mgr = make_flavor_manager()
        flavor = make_flavor(
            min_qubits=4,
            max_qubits=None,
            gate_fidelity_1q_min=None,
            gate_fidelity_2q_min=None,
            extra_properties=None,
        )
        with patch.object(mgr, "get_flavor", return_value=flavor):
            specs = mgr.get_flavor_specs(flavor.id)
        assert specs == {"min_qubits": 4}


# ------------------------------------------------------------------ #
# FlavorManager.get_visible_flavor / get_visible_flavors
# ------------------------------------------------------------------ #
class TestFlavorManagerVisible:
    """Tests for FlavorManager visible scoping methods."""

    def test_get_visible_flavor_empty_id(self):
        mgr = make_flavor_manager()
        assert mgr.get_visible_flavor("") is None

    def test_get_visible_flavor_found(self):
        mgr = make_flavor_manager()
        flavor = make_flavor(is_public=False)
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_flavor_by_uuid.return_value = (
                True,
                None,
                flavor,
            )
            result = mgr.get_visible_flavor(
                flavor.id, project_id=flavor.project_id
            )
            assert result is flavor

    def test_get_visible_flavor_not_found(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_flavor_by_uuid.return_value = (
                True,
                None,
                None,
            )
            assert mgr.get_visible_flavor("x", project_id="p") is None

    def test_get_visible_flavor_repo_error(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_flavor_by_uuid.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_visible_flavor("x", project_id="p") is None

    def test_get_flavors_no_filter(self):
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        f2 = make_flavor(name="b")
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavors.return_value = (True, None, [f1, f2])
            result = mgr.get_flavors()
            assert len(result) == 2

    def test_get_flavors_repo_failure(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavors.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_flavors() == []

    def test_get_flavors_with_name_filter(self):
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        f2 = make_flavor(name="b")
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavors.return_value = (True, None, [f1, f2])
            result = mgr.get_flavors(filters={"flavor_name": "a"})
            assert len(result) == 1
            assert result[0].name == "a"

    def test_get_flavors_with_ids_filter(self):
        """get_flavors should pass flavor_ids as DB-level id filter."""
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavors.return_value = (True, None, [f1])
            result = mgr.get_flavors(filters={"flavor_ids": [f1.id]})
            assert len(result) == 1
            # Verify DB-level filter was passed
            call_kwargs = mock_repo.get_flavors.call_args.kwargs
            assert call_kwargs["filters"] == {"id": [f1.id]}

    def test_get_visible_flavors_no_filter(self):
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_flavors.return_value = (
                True,
                None,
                [f1],
            )
            result = mgr.get_visible_flavors(project_id="p")
            assert len(result) == 1

    def test_get_visible_flavors_repo_failure(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_flavors.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_visible_flavors(project_id="p") == []

    def test_get_visible_flavors_with_name_filter(self):
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        f2 = make_flavor(name="b")
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_flavors.return_value = (
                True,
                None,
                [f1, f2],
            )
            result = mgr.get_visible_flavors(
                filters={"flavor_name": "b"}, project_id="p"
            )
            assert len(result) == 1
            assert result[0].name == "b"

    def test_get_visible_flavors_with_ids_filter(self):
        """get_visible_flavors should filter by flavor_ids in-memory."""
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        f2 = make_flavor(name="b")
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_flavors.return_value = (
                True,
                None,
                [f1, f2],
            )
            result = mgr.get_visible_flavors(
                filters={"flavor_ids": [f1.id]}, project_id="p"
            )
            assert len(result) == 1
            assert str(result[0].id) == str(f1.id)


# ------------------------------------------------------------------ #
# FlavorManager.create / update / delete
# ------------------------------------------------------------------ #
class TestFlavorManagerMutations:
    """Tests for FlavorManager create/update/delete."""

    def test_create_flavor(self):
        mgr = make_flavor_manager()
        flavor = make_flavor()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.create_flavor.return_value = (True, None, flavor)
            ok, err, result = mgr.create_flavor({"name": "x"})
            assert ok is True
            assert result is flavor

    def test_update_flavor(self):
        mgr = make_flavor_manager()
        flavor = make_flavor()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.update_flavor.return_value = (True, None, flavor)
            ok, err, result = mgr.update_flavor(
                flavor.id, {"name": "new"}, db_filters={}
            )
            assert ok is True
            assert result is flavor

    def test_delete_flavor(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_flavor.return_value = (True, None)
            ok, err = mgr.delete_flavor("some-id", db_filters={})
            assert ok is True

    def test_delete_flavor_failure(self):
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_flavor.return_value = (
                False,
                "Flavor not found",
            )
            ok, err = mgr.delete_flavor("some-id", db_filters={})
            assert ok is False
            assert "not found" in err

    def test_delete_flavors_batch(self):
        """delete_flavors should iterate and collect per-flavor results."""
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_flavor.side_effect = [
                (True, None),
                (False, "not found"),
            ]
            results = mgr.delete_flavors(["id1", "id2"], db_filters={})
            assert len(results) == 2
            assert results[0] == ("id1", True, None)
            assert results[1] == ("id2", False, "not found")

    def test_delete_flavors_batch_all_success(self):
        """delete_flavors should return all success when all pass."""
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_flavor.return_value = (True, None)
            results = mgr.delete_flavors(["id1", "id2", "id3"], db_filters={})
            assert len(results) == 3
            for fid, success, err in results:
                assert success is True
                assert err is None

    def test_delete_flavors_dedup(self):
        """delete_flavors deduplicates flavor_ids preserving order."""
        mgr = make_flavor_manager()
        with patch(
            "wy_qcos.flavor.flavor_manager.FlavorRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_flavor.return_value = (True, None)
            results = mgr.delete_flavors(["id1", "id1", "id2"], db_filters={})
            assert len(results) == 2
            assert results[0][0] == "id1"
            assert results[1][0] == "id2"
            # delete_flavor called only twice (deduped)
            assert mock_repo.delete_flavor.call_count == 2


# ------------------------------------------------------------------ #
# FlavorManager.get_flavor_responses
# ------------------------------------------------------------------ #
class TestFlavorManagerResponses:
    """Tests for FlavorManager.get_flavor_responses."""

    def test_no_project_id_uses_get_flavors(self):
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        with patch.object(mgr, "get_flavors", return_value=[f1]) as mock_get:
            with patch.object(
                mgr, "get_flavor_device_groups", return_value=[]
            ):
                result = mgr.get_flavor_responses()
                assert len(result) == 1
                assert result[0].device_groups == []
            mock_get.assert_called_once()

    def test_with_project_id_uses_get_visible_flavors(self):
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        with patch.object(
            mgr, "get_visible_flavors", return_value=[f1]
        ) as mock_get:
            with patch.object(
                mgr, "get_flavor_device_groups", return_value=[]
            ):
                result = mgr.get_flavor_responses(project_id="p")
                assert len(result) == 1
                assert result[0].device_groups == []
            mock_get.assert_called_once()

    def test_resolves_device_groups(self):
        """get_flavor_responses resolves device_groups as UUID list."""
        mgr = make_flavor_manager()
        f1 = make_flavor(name="a")
        dg_id = str(uuid.uuid4())
        with patch.object(mgr, "get_flavors", return_value=[f1]):
            with patch.object(
                mgr, "get_flavor_device_groups", return_value=[dg_id]
            ):
                result = mgr.get_flavor_responses()
                assert len(result) == 1
                assert result[0].device_groups == [uuid.UUID(dg_id)]


# ------------------------------------------------------------------ #
# FlavorManager.init_db
# ------------------------------------------------------------------ #
class TestFlavorManagerInitDb:
    """Tests for FlavorManager.init_db default flavor seeding."""

    def test_init_db_creates_defaults(self):
        engine = MagicMock()
        with (
            patch(
                "wy_qcos.flavor.flavor_manager.FlavorRepository"
            ) as mock_repo_cls,
            patch("wy_qcos.flavor.flavor_manager.create_db_session"),
        ):
            mock_repo = mock_repo_cls.return_value
            # all default flavors do not exist yet
            mock_repo.get_flavor_by_uuid.return_value = (
                True,
                None,
                None,
            )
            mock_repo.create_flavor.return_value = (True, None, None)

            mgr = FlavorManager.__new__(FlavorManager)
            mgr._db_engine = engine
            mgr.init_db()

            assert mock_repo.create_flavor.call_count == len(DEFAULT_FLAVORS)

    def test_init_db_skips_existing(self):
        engine = MagicMock()
        with (
            patch(
                "wy_qcos.flavor.flavor_manager.FlavorRepository"
            ) as mock_repo_cls,
            patch("wy_qcos.flavor.flavor_manager.create_db_session"),
        ):
            mock_repo = mock_repo_cls.return_value
            existing = make_flavor()
            mock_repo.get_flavor_by_uuid.return_value = (
                True,
                None,
                existing,
            )

            mgr = FlavorManager.__new__(FlavorManager)
            mgr._db_engine = engine
            mgr.init_db()

            mock_repo.create_flavor.assert_not_called()

    def test_init_db_create_error_logged(self):
        engine = MagicMock()
        with (
            patch(
                "wy_qcos.flavor.flavor_manager.FlavorRepository"
            ) as mock_repo_cls,
            patch("wy_qcos.flavor.flavor_manager.create_db_session"),
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_flavor_by_uuid.return_value = (
                True,
                None,
                None,
            )
            mock_repo.create_flavor.return_value = (
                False,
                "db error",
                None,
            )

            mgr = FlavorManager.__new__(FlavorManager)
            mgr._db_engine = engine
            mgr.init_db()

            # should not raise, errors are logged
            assert mock_repo.create_flavor.call_count == len(DEFAULT_FLAVORS)


# ------------------------------------------------------------------ #
# API route: create_flavor
# ------------------------------------------------------------------ #
class TestCreateFlavorRoute:
    """Tests for create_flavor API route."""

    def _make_request(self, **kwargs):
        defaults = {
            "name": "new-flavor",
            "description": "desc",
            "is_public": True,
            "device_groups": ["00000000-0000-4000-8000-000000000003"],
        }
        defaults.update(kwargs)
        return schemas.CreateFlavorRequest(**defaults)

    def _setup_scheduler(self, mock_sched, flavor_mgr):
        mock_sched.get_flavor_manager.return_value = flavor_mgr

    def test_create_flavor_success(self):
        flavor = make_flavor(name="new-flavor")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.validate_device_groups.return_value = (True, None)
        mgr.create_flavor.return_value = (True, None, flavor)
        mock_sched.get_flavor_manager.return_value = mgr

        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            body = self._make_request()
            result = create_flavor(body, mock_request, auth_data=None)
            assert result.name == "new-flavor"

    def test_create_flavor_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_flavor_manager.return_value = None
        body = self._make_request()
        mock_request = MagicMock()
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_empty_name(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(name="")
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_duplicate_name(self):
        existing = make_flavor(name="dup-name")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = [existing]
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(name="dup-name")
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_project_not_found(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(
            project_id="00000000-0000-4000-8000-000000000099"
        )
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = None
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_bad_extra_properties(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (
            False,
            "bad property",
        )
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(extra_properties={"badkey": "val"})
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_repo_failure(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.create_flavor.return_value = (False, "db error", None)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request()
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_with_auth_project_id(self):
        """project_id defaults from auth_data."""
        flavor = make_flavor(name="new-flavor")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.validate_device_groups.return_value = (True, None)
        mgr.create_flavor.return_value = (True, None, flavor)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request()
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        auth_data = {
            "project_id": Constant.ADMIN_PROJECT_ID,
        }
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = create_flavor(body, mock_request, auth_data=auth_data)
            assert result.name == "new-flavor"

    def test_create_flavor_invalid_qubits_range(self):
        """min_qubits > max_qubits should raise an error."""
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.validate_device_groups.return_value = (True, None)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(min_qubits=10, max_qubits=5)
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_invalid_fidelity_1q(self):
        """gate_fidelity_1q_min > 1 should raise an error."""
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.validate_device_groups.return_value = (True, None)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(gate_fidelity_1q_min=1.5)
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_invalid_fidelity_2q(self):
        """gate_fidelity_2q_min < 0 should raise an error."""
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.validate_device_groups.return_value = (True, None)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(gate_fidelity_2q_min=-0.1)
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_flavor(body, mock_request, auth_data=None)

    def test_create_flavor_valid_fidelity_boundary(self):
        """gate_fidelity values of 0 and 1 (boundaries) should pass."""
        flavor = make_flavor(name="new-flavor")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.validate_device_groups.return_value = (True, None)
        mgr.create_flavor.return_value = (True, None, flavor)
        mock_sched.get_flavor_manager.return_value = mgr
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            # boundary: 0
            body = self._make_request(
                gate_fidelity_1q_min=0.0, gate_fidelity_2q_min=0.0
            )
            result = create_flavor(body, mock_request, auth_data=None)
            assert result.name == "new-flavor"
            # boundary: 1
            body = self._make_request(
                gate_fidelity_1q_min=1.0, gate_fidelity_2q_min=1.0
            )
            result = create_flavor(body, mock_request, auth_data=None)
            assert result.name == "new-flavor"


# ------------------------------------------------------------------ #
# API route: update_flavor
# ------------------------------------------------------------------ #
class TestUpdateFlavorRoute:
    """Tests for update_flavor API route."""

    def _make_request(self, flavor_id, **kwargs):
        # Only pass explicitly-provided kwargs so that model_fields_set
        # reflects what the caller intends to update/clear.
        return schemas.UpdateFlavorRequest(flavor_id=flavor_id, **kwargs)

    def test_update_flavor_success(self):
        flavor_id = str(uuid.uuid4())
        existing = make_flavor(flavor_id=flavor_id)
        updated = make_flavor(flavor_id=flavor_id, name="updated")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.get_flavor.return_value = existing
        mgr.validate_device_groups.return_value = (True, None)
        mgr.update_flavor.return_value = (True, None, updated)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, name="updated")
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = update_flavor(body, MagicMock(), auth_data=None)
            assert result.name == "updated"

    def test_update_flavor_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_flavor_manager.return_value = None
        body = self._make_request(str(uuid.uuid4()), name="x")
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_no_fields(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(str(uuid.uuid4()))
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_duplicate_name(self):
        flavor_id = str(uuid.uuid4())
        other = make_flavor(name="taken")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = [other]
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, name="taken")
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_project_not_found(self):
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(
            flavor_id,
            project_id="00000000-0000-4000-8000-000000000099",
        )
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_project_manager",
                return_value=MagicMock(),
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_bad_extra_properties(self):
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (
            False,
            "bad property",
        )
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, extra_properties={"bad": "v"})
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_extra_properties_not_found(self):
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.get_flavor.return_value = None
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(
            flavor_id, extra_properties={"qc:devices": "x"}
        )
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_clear_extra_properties(self):
        """Explicitly passing extra_properties=None clears the field."""
        flavor_id = str(uuid.uuid4())
        existing = make_flavor(
            flavor_id=flavor_id, extra_properties={"qc:devices": "old"}
        )
        updated = make_flavor(flavor_id=flavor_id, extra_properties=None)
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.get_flavor.return_value = existing
        mgr.update_flavor.return_value = (True, None, updated)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, extra_properties=None)
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = update_flavor(body, MagicMock(), auth_data=None)
            assert result is not None
            # update_flavor should be called with extra_properties=None
            call_data = mgr.update_flavor.call_args[0][1]
            assert call_data["extra_properties"] is None

    def test_update_flavor_clear_device_groups(self):
        """Explicitly passing device_groups=None clears mappings."""
        flavor_id = str(uuid.uuid4())
        existing = make_flavor(flavor_id=flavor_id)
        updated = make_flavor(flavor_id=flavor_id)
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.get_flavor.return_value = existing
        mgr.update_flavor.return_value = (True, None, updated)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, device_groups=None)
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = update_flavor(body, MagicMock(), auth_data=None)
            assert result is not None
            # update_flavor should be called with device_groups=[]
            call_data = mgr.update_flavor.call_args[0][1]
            assert call_data["device_groups"] == []

    def test_update_flavor_merge_extra_properties(self):
        flavor_id = str(uuid.uuid4())
        existing = make_flavor(
            flavor_id=flavor_id, extra_properties={"qc:devices": "old"}
        )
        updated = make_flavor(
            flavor_id=flavor_id,
            extra_properties={"qc:devices": "new"},
        )
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.validate_extra_properties.return_value = (True, None)
        mgr.validate_device_groups.return_value = (True, None)
        mgr.get_flavor.return_value = existing
        mgr.update_flavor.return_value = (True, None, updated)
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(
            flavor_id, extra_properties={"qc:devices": "new"}
        )
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = update_flavor(body, MagicMock(), auth_data=None)
            assert result is not None

    def test_update_flavor_repo_failure(self):
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.update_flavor.return_value = (
            False,
            "db error",
            None,
        )
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, name="x")
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_invalid_qubits_range(self):
        """Updating min_qubits > max_qubits should raise an error."""
        flavor_id = str(uuid.uuid4())
        existing = make_flavor(flavor_id=flavor_id)
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.get_flavor.return_value = existing
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, min_qubits=10, max_qubits=5)
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_invalid_fidelity_1q(self):
        """Updating gate_fidelity_1q_min > 1 should raise an error."""
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mock_sched.get_flavor_manager.return_value = mgr
        body = self._make_request(flavor_id, gate_fidelity_1q_min=1.5)
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_flavor(body, MagicMock(), auth_data=None)

    def test_update_flavor_valid_fidelity_boundary(self):
        """Updating gate_fidelity to boundary values 0 and 1 should pass."""
        flavor_id = str(uuid.uuid4())
        updated = make_flavor(flavor_id=flavor_id, name="updated")
        existing = make_flavor(flavor_id=flavor_id)
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavors.return_value = []
        mgr.get_flavor.return_value = existing
        mgr.update_flavor.return_value = (True, None, updated)
        mock_sched.get_flavor_manager.return_value = mgr
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            # boundary: 0
            body = self._make_request(
                flavor_id,
                gate_fidelity_1q_min=0.0,
                gate_fidelity_2q_min=0.0,
            )
            result = update_flavor(body, MagicMock(), auth_data=None)
            assert result is not None
            # boundary: 1
            body = self._make_request(
                flavor_id,
                gate_fidelity_1q_min=1.0,
                gate_fidelity_2q_min=1.0,
            )
            result = update_flavor(body, MagicMock(), auth_data=None)
            assert result is not None


# ------------------------------------------------------------------ #
# API route: get_flavor / get_flavors
# ------------------------------------------------------------------ #
class TestGetFlavorRoute:
    """Tests for get_flavor and get_flavors API routes."""

    def test_get_flavor_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_flavor_manager.return_value = None
        body = schemas.GetFlavorRequest(flavor_id=str(uuid.uuid4()))
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                get_flavor(body, auth_data=None)

    def test_get_flavor_super_admin(self):
        flavor = make_flavor()
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavor.return_value = flavor
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.GetFlavorRequest(flavor_id=flavor.id)
        auth_data = {"is_super_admin": True}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            result = get_flavor(body, auth_data=auth_data)
            assert result.name == flavor.name

    def test_get_flavor_non_admin_visible(self):
        flavor = make_flavor()
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_visible_flavor.return_value = flavor
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.GetFlavorRequest(flavor_id=flavor.id)
        auth_data = {"is_super_admin": False, "project_id": "p"}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            result = get_flavor(body, auth_data=auth_data)
            assert result.name == flavor.name

    def test_get_flavor_not_found_raises(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavor.return_value = None
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.GetFlavorRequest(flavor_id=str(uuid.uuid4()))
        auth_data = {"is_super_admin": True}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                get_flavor(body, auth_data=auth_data)

    def test_get_flavor_non_admin_not_visible_raises(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_visible_flavor.return_value = None
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.GetFlavorRequest(flavor_id=str(uuid.uuid4()))
        auth_data = {"is_super_admin": False, "project_id": "p"}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                get_flavor(body, auth_data=auth_data)

    def test_get_flavors_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_flavor_manager.return_value = None
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                get_flavors(body=None, auth_data=None)

    def test_get_flavors_super_admin(self):
        f1 = make_flavor(name="a")
        f2 = make_flavor(name="b")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavor_responses.return_value = [f1, f2]
        mock_sched.get_flavor_manager.return_value = mgr
        auth_data = {"is_super_admin": True}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            result = get_flavors(body=None, auth_data=auth_data)
            assert len(result) == 2
            # super admin passes project_id=None to get_flavor_responses
            call_kwargs = mgr.get_flavor_responses.call_args.kwargs
            assert call_kwargs.get("project_id") is None

    def test_get_flavors_non_admin(self):
        f1 = make_flavor(name="a")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_flavor_responses.return_value = [f1]
        mock_sched.get_flavor_manager.return_value = mgr
        auth_data = {"is_super_admin": False, "project_id": "p"}
        body = schemas.GetFlavorsRequest(filters={"flavor_name": "a"})
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            result = get_flavors(body=body, auth_data=auth_data)
            assert len(result) == 1
            # non-admin passes project_id for visibility scoping
            call_kwargs = mgr.get_flavor_responses.call_args.kwargs
            assert call_kwargs.get("project_id") == "p"


# ------------------------------------------------------------------ #
# API route: delete_flavors (batch)
# ------------------------------------------------------------------ #
class TestDeleteFlavorsRoute:
    """Tests for delete_flavors API route."""

    def test_delete_flavors_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_flavor_manager.return_value = None
        body = schemas.DeleteFlavorsRequest(flavor_ids=[str(uuid.uuid4())])
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                delete_flavors(body, auth_data=None)

    def test_delete_flavors_success(self):
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_flavors.return_value = [(flavor_id, True, None)]
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.DeleteFlavorsRequest(flavor_ids=[flavor_id])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = delete_flavors(body, auth_data=None)
            assert len(result.results) == 1
            assert str(result.results[0].flavor_id) == flavor_id
            assert result.results[0].success is True

    def test_delete_flavors_partial_failure(self):
        """Batch delete should return per-flavor results, not abort."""
        fid1 = str(uuid.uuid4())
        fid2 = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_flavors.return_value = [
            (fid1, True, None),
            (fid2, False, "Flavor not found"),
        ]
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.DeleteFlavorsRequest(flavor_ids=[fid1, fid2])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = delete_flavors(body, auth_data=None)
            assert len(result.results) == 2
            assert result.results[0].success is True
            assert result.results[1].success is False
            assert "not found" in result.results[1].error

    def test_delete_flavors_dedup(self):
        """Duplicate flavor_ids are deduplicated in the manager layer.

        The route forwards the raw list; dedup happens in
        FlavorManager.delete_flavors.
        """
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_flavors.return_value = [(flavor_id, True, None)]
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.DeleteFlavorsRequest(flavor_ids=[flavor_id, flavor_id])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
                mock_sched,
            ),
        ):
            result = delete_flavors(body, auth_data=None)
            assert len(result.results) == 1
            # route passes the raw (un-deduped) list to the manager
            call_args = mgr.delete_flavors.call_args.args
            assert call_args[0] == [flavor_id, flavor_id]

    def test_delete_flavors_super_admin_no_project_filter(self):
        """Super admin should have project_id filter removed."""
        flavor_id = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_flavors.return_value = [(flavor_id, True, None)]
        mock_sched.get_flavor_manager.return_value = mgr
        body = schemas.DeleteFlavorsRequest(flavor_ids=[flavor_id])
        auth_data = {
            "is_super_admin": True,
            "is_project_admin": True,
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_id": Constant.ANONYMOUS_USER_ID,
        }
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.flavor.scheduler",
            mock_sched,
        ):
            result = delete_flavors(body, auth_data=auth_data)
            assert result is not None
            call_args = mgr.delete_flavors.call_args
            db_filters = call_args.kwargs.get("db_filters", {})
            assert "project_id" not in db_filters


# ------------------------------------------------------------------ #
# FlavorRepository (using in-memory SQLite)
# ------------------------------------------------------------------ #
class TestFlavorRepository:
    """Tests for FlavorRepository DB operations using mocks.

    Uses MagicMock for the db_session to avoid SQLite/GUID type
    incompatibilities while still exercising the repository logic.
    """

    @pytest.fixture
    def repo_setup(self):
        """Build a FlavorRepository with a mocked session."""
        from wy_qcos.db.repositories.flavor import (
            FlavorRepository,
        )

        mock_session = MagicMock()
        repo = FlavorRepository(mock_session)
        return repo, mock_session

    def test_create_flavor_success(self, repo_setup):
        repo, session = repo_setup
        data = {
            "id": str(uuid.uuid4()),
            "name": "test-repo",
            "project_id": Constant.ADMIN_PROJECT_ID,
        }
        ok, err, flavor = repo.create_flavor(data)
        assert ok is True
        assert err is None
        session.add.assert_called_once()
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

    def test_create_flavor_failure(self, repo_setup):
        repo, session = repo_setup
        session.commit.side_effect = Exception("db error")
        data = {
            "id": str(uuid.uuid4()),
            "name": "fail",
            "project_id": Constant.ADMIN_PROJECT_ID,
        }
        ok, err, flavor = repo.create_flavor(data)
        assert ok is False
        assert "db error" in err
        assert flavor is None
        session.rollback.assert_called_once()

    def test_get_flavor_by_uuid(self, repo_setup):
        repo, session = repo_setup
        flavor = make_flavor()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            ok, err, result = repo.get_flavor_by_uuid(flavor.id)
        assert ok is True
        assert result is flavor

    def test_get_flavor_by_uuid_not_found(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err, result = repo.get_flavor_by_uuid("missing")
        assert ok is True
        assert result is None

    def test_get_flavor_by_uuid_error(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(False, "db error", None)
        ):
            ok, err, result = repo.get_flavor_by_uuid("x")
        assert ok is False
        assert "db error" in err

    def test_get_flavor_by_name(self, repo_setup):
        repo, _ = repo_setup
        flavor = make_flavor(name="by-name")
        with patch.object(
            repo, "get_by_attr", return_value=(True, None, flavor)
        ):
            ok, err, result = repo.get_flavor_by_name("by-name")
        assert ok is True
        assert result is flavor

    def test_get_flavor_by_name_not_found(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_attr", return_value=(True, None, None)
        ):
            ok, err, result = repo.get_flavor_by_name("missing")
        assert ok is True
        assert result is None

    def test_get_visible_flavor_public(self, repo_setup):
        """Public flavor visible to any project."""
        repo, session = repo_setup
        flavor = make_flavor(is_public=True)
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = flavor
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        ok, err, result = repo.get_visible_flavor_by_uuid(
            flavor.id, project_id="other"
        )
        assert ok is True
        assert result is flavor

    def test_get_visible_flavor_not_found(self, repo_setup):
        repo, session = repo_setup
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        ok, err, result = repo.get_visible_flavor_by_uuid(
            "x", project_id="other"
        )
        assert ok is True
        assert result is None

    def test_get_visible_flavor_error(self, repo_setup):
        repo, session = repo_setup
        session.execute.side_effect = Exception("db error")
        ok, err, result = repo.get_visible_flavor_by_uuid(
            "x", project_id="other"
        )
        assert ok is False
        assert "db error" in err

    def test_get_visible_flavors_success(self, repo_setup):
        repo, session = repo_setup
        f1 = make_flavor(name="a")
        f2 = make_flavor(name="b")
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [f1, f2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        ok, err, flavors = repo.get_visible_flavors(project_id="p")
        assert ok is True
        assert len(flavors) == 2

    def test_get_visible_flavors_error(self, repo_setup):
        repo, session = repo_setup
        session.execute.side_effect = Exception("db error")
        ok, err, flavors = repo.get_visible_flavors(project_id="p")
        assert ok is False
        assert "db error" in err

    def test_get_flavors_all(self, repo_setup):
        repo, _ = repo_setup
        f1 = make_flavor(name="all-1")
        with patch.object(repo, "get_all", return_value=(True, None, [f1])):
            ok, err, flavors = repo.get_flavors()
        assert ok is True
        assert len(flavors) == 1

    def test_get_flavors_with_filters(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(repo, "get_all", return_value=(True, None, [])):
            ok, err, flavors = repo.get_flavors(filters={"name": "x"})
        assert ok is True

    def test_delete_flavor_success(self, repo_setup):
        repo, session = repo_setup
        flavor = make_flavor()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            ok, err = repo.delete_flavor(flavor.id)
        assert ok is True
        session.delete.assert_called_once_with(flavor)
        # delete_flavor calls commit for mapping deletion and
        # flavor deletion, so commit may be called multiple times.
        session.commit.assert_called()
        assert session.commit.call_count >= 1

    def test_delete_flavor_not_found(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err = repo.delete_flavor("missing-id")
        assert ok is False
        assert "not found" in err

    def test_delete_flavor_get_error(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo,
            "get_by_uuid",
            return_value=(False, "db error", None),
        ):
            ok, err = repo.delete_flavor("x")
        assert ok is False
        assert "db error" in err

    def test_delete_flavor_exception(self, repo_setup):
        repo, session = repo_setup
        flavor = make_flavor()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            session.delete.side_effect = Exception("delete error")
            ok, err = repo.delete_flavor(flavor.id)
        assert ok is False
        assert "delete error" in err
        session.rollback.assert_called_once()

    def test_delete_flavor_with_project_filter_match(self, repo_setup):
        """Delete with matching project_id filter succeeds."""
        repo, session = repo_setup
        flavor = make_flavor()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            ok, err = repo.delete_flavor(
                flavor.id,
                filters={"project_id": Constant.ADMIN_PROJECT_ID},
            )
        assert ok is True

    def test_delete_flavor_with_project_filter_mismatch(self, repo_setup):
        """Delete with mismatched project_id filter fails.

        This is the scenario that caused the original bug: an
        anonymous super admin's project_id (DEFAULT_PROJECT_ID)
        does not match the flavor's project_id (ADMIN_PROJECT_ID).
        """
        repo, _ = repo_setup
        flavor = make_flavor()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err = repo.delete_flavor(
                flavor.id,
                filters={"project_id": Constant.DEFAULT_PROJECT_ID},
            )
        assert ok is False
        assert "not found" in err

    def test_update_flavor_success(self, repo_setup):
        repo, session = repo_setup
        flavor = make_flavor(description="old")
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            ok, err, result = repo.update_flavor(
                flavor.id, {"description": "new"}
            )
        assert ok is True
        assert flavor.description == "new"
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

    def test_update_flavor_not_found(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err, result = repo.update_flavor("missing", {"name": "x"})
        assert ok is False
        assert "not found" in err

    def test_update_flavor_get_error(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo,
            "get_by_uuid",
            return_value=(False, "db error", None),
        ):
            ok, err, result = repo.update_flavor("x", {"name": "y"})
        assert ok is False
        assert "db error" in err

    def test_update_flavor_exception(self, repo_setup):
        repo, session = repo_setup
        flavor = make_flavor()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            session.commit.side_effect = Exception("commit error")
            ok, err, result = repo.update_flavor(flavor.id, {"name": "new"})
        assert ok is False
        assert "commit error" in err
        session.rollback.assert_called_once()

    def test_update_flavor_with_filter_match(self, repo_setup):
        repo, session = repo_setup
        flavor = make_flavor(name="old")
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            ok, err, result = repo.update_flavor(
                flavor.id,
                {"name": "new"},
                filters={"project_id": Constant.ADMIN_PROJECT_ID},
            )
        assert ok is True

    def test_update_flavor_with_filter_mismatch(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err, result = repo.update_flavor(
                "x",
                {"name": "new"},
                filters={"project_id": Constant.DEFAULT_PROJECT_ID},
            )
        assert ok is False
        assert "not found" in err

    def test_update_flavor_unknown_field_ignored(self, repo_setup):
        """Fields not on the model should be ignored."""
        repo, session = repo_setup
        flavor = make_flavor()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, flavor)
        ):
            ok, err, result = repo.update_flavor(
                flavor.id, {"unknown_field": "val"}
            )
        assert ok is True
        assert not hasattr(flavor, "unknown_field")

    def test_create_flavor_commit_exception_path(self, repo_setup):
        """create_flavor exception triggers rollback."""
        repo, session = repo_setup
        session.add.side_effect = Exception("add error")
        data = {
            "id": str(uuid.uuid4()),
            "name": "x",
            "project_id": Constant.ADMIN_PROJECT_ID,
        }
        ok, err, flavor = repo.create_flavor(data)
        assert ok is False
        assert "add error" in err
        session.rollback.assert_called_once()


# ------------------------------------------------------------------ #
# get_db_filters (flavor-relevant paths)
# ------------------------------------------------------------------ #
class TestGetDbFilters:
    """Tests for get_db_filters focusing on flavor scenarios."""

    def test_no_auth_data_returns_empty(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        result = get_db_filters(None)
        assert result == {}

    def test_super_admin_allow_removes_project_id(self):
        """Super admin should have project_id filter removed (not kept).

        This is the fix for the delete-flavor bug.
        """
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": True,
            "is_project_admin": True,
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_id": Constant.ANONYMOUS_USER_ID,
        }
        result = get_db_filters(auth_data, allow_super_admin=True)
        # project_id should be removed for super admin
        assert "project_id" not in result
        assert "user_id" not in result

    def test_super_admin_not_allowed_keeps_project_id(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": True,
            "is_project_admin": False,
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_id": Constant.ANONYMOUS_USER_ID,
        }
        result = get_db_filters(auth_data, allow_super_admin=False)
        # project_id kept when allow_super_admin is False
        assert result.get("project_id") == Constant.DEFAULT_PROJECT_ID

    def test_project_admin_allow_removes_user_id(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": False,
            "is_project_admin": True,
            "project_id": "proj-1",
            "user_id": "user-1",
        }
        result = get_db_filters(auth_data, allow_project_admin=True)
        assert "user_id" not in result

    def test_non_admin_filters_by_own_project(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": False,
            "is_project_admin": False,
            "project_id": "my-proj",
            "user_id": "my-user",
        }
        result = get_db_filters(auth_data)
        assert result["project_id"] == "my-proj"
        assert result["user_id"] == "my-user"

    def test_filter_flavor_ids(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": True,
            "is_project_admin": True,
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_id": Constant.ANONYMOUS_USER_ID,
        }
        flavor_ids = [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ]
        result = get_db_filters(
            auth_data,
            filters={"flavor_ids": flavor_ids},
            allow_super_admin=True,
        )
        assert result["id"] == flavor_ids

    def test_filter_job_ids(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": True,
            "is_project_admin": True,
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_id": Constant.ANONYMOUS_USER_ID,
        }
        job_ids = ["job-1", "job-2"]
        result = get_db_filters(
            auth_data,
            filters={"job_ids": job_ids},
            allow_super_admin=True,
        )
        assert result["id"] == job_ids

    def test_super_admin_all_projects_flag(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": True,
            "is_project_admin": False,
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_id": Constant.ANONYMOUS_USER_ID,
        }
        result = get_db_filters(
            auth_data,
            filters={"all_projects": True},
            allow_super_admin=False,
        )
        # all_projects=True means no project_id filter
        assert "project_id" not in result

    def test_non_admin_filter_project_mismatch(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": False,
            "is_project_admin": False,
            "project_id": "my-proj",
            "user_id": "my-user",
        }
        result = get_db_filters(
            auth_data, filters={"project_id": "other-proj"}
        )
        # mismatched project_id should be set to INVALID
        assert result["project_id"] == Constant.INVALID_PROJECT_ID

    def test_super_admin_filter_project_match(self):
        from wy_qcos.db.utils.db_utils import get_db_filters

        auth_data = {
            "is_super_admin": True,
            "is_project_admin": False,
            "project_id": "my-proj",
            "user_id": "my-user",
        }
        result = get_db_filters(auth_data, filters={"project_id": "my-proj"})
        assert result["project_id"] == "my-proj"


# ------------------------------------------------------------------ #
# FlavorNotFoundError
# ------------------------------------------------------------------ #
class TestFlavorNotFoundError:
    """Tests for FlavorNotFoundError exception."""

    def test_error_attributes(self):
        err = FlavorNotFoundError("test message")
        assert err.module_name == "Flavor"
        assert err.error_code == -201
        assert err.err_type == "FlavorNotFoundError"
        assert "test message" in err.message

    def test_error_get_msgs(self):
        err = FlavorNotFoundError("not found")
        msgs = err.get_err_msgs()
        assert "[Flavor]" in msgs
        assert "FlavorNotFoundError" in msgs
        assert "not found" in msgs

    def test_error_is_base_exception(self):
        from wy_qcos.common.errors import BaseException

        err = FlavorNotFoundError("x")
        assert isinstance(err, BaseException)
        assert isinstance(err, Exception)


# ------------------------------------------------------------------ #
# Flavor model
# ------------------------------------------------------------------ #
class TestFlavorModel:
    """Tests for Flavor model."""

    def test_flavor_table_name(self):
        assert Flavor.__tablename__ == "flavors"

    def test_flavor_columns(self):
        cols = {c.name for c in Flavor.__table__.columns}
        expected = {
            "id",
            "project_id",
            "name",
            "description",
            "is_public",
            "min_qubits",
            "max_qubits",
            "gate_fidelity_1q_min",
            "gate_fidelity_2q_min",
            "extra_properties",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(cols)
