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
from wy_qcos.api.posiq.routes_jsonrpc.device_group import (
    create_device_group,
    delete_device_groups,
    get_device_group,
    get_device_groups,
    update_device_group,
)
from wy_qcos.common.constant import Constant
from wy_qcos.db.models import DeviceGroup
from wy_qcos.device.errors import DeviceGroupNotFoundError
from wy_qcos.device.device_group_manager import (
    DeviceGroupManager,
)
from wy_qcos.common.flavor_constant import FlavorConstant
from wy_qcos.scheduler.filters.device_group import DeviceGroupFilter
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def make_group(
    group_id=None,
    name="test-group",
    project_id=None,
    description="desc",
    device_names=None,
    is_public=True,
):
    """Build a DeviceGroup-like SimpleNamespace for testing."""
    if group_id is None:
        group_id = str(uuid.uuid4())
    if project_id is None:
        project_id = Constant.ADMIN_PROJECT_ID
    if device_names is None:
        device_names = ["dummy", "qutip_sim"]
    return SimpleNamespace(
        id=group_id,
        project_id=project_id,
        name=name,
        description=description,
        device_names=device_names,
        is_public=is_public,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_dg_manager():
    """Build a DeviceGroupManager with a mocked db_engine."""
    mock_engine = MagicMock()
    mgr = DeviceGroupManager.__new__(DeviceGroupManager)
    mgr._db_engine = mock_engine
    return mgr


def make_device_state(name="dummy", **kwargs):
    """Build a DeviceState for filter testing."""
    ds = DeviceState.__new__(DeviceState)
    ds.device = MagicMock()
    ds.name = name
    ds.status = "ACTIVE"
    ds.enable = True
    ds.max_qubits = kwargs.get("max_qubits", 10)
    for k, v in kwargs.items():
        setattr(ds, k, v)
    return ds


def make_spec(flavor_specs=None, extra_specs=None, **kwargs):
    """Build a RequestSpec for filter testing."""
    return RequestSpec(
        code_type=kwargs.get("code_type", "qasm"),
        num_qubits=kwargs.get("num_qubits", 0),
        flavor_id=kwargs.get("flavor_id"),
        flavor_specs=flavor_specs or {},
        extra_specs=extra_specs or {},
    )


# ------------------------------------------------------------------ #
# DeviceGroupManager get methods
# ------------------------------------------------------------------ #
class TestDeviceGroupManagerGet:
    """Tests for DeviceGroupManager get methods."""

    def test_get_device_group_empty_id(self):
        mgr = make_dg_manager()
        assert mgr.get_device_group("") is None

    def test_get_device_group_by_name_empty(self):
        mgr = make_dg_manager()
        assert mgr.get_device_group_by_name("") is None

    def test_get_visible_device_group_empty_id(self):
        mgr = make_dg_manager()
        assert mgr.get_visible_device_group("") is None

    def test_get_device_group_found(self):
        mgr = make_dg_manager()
        group = make_group()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_group_by_uuid.return_value = (
                True,
                None,
                group,
            )
            result = mgr.get_device_group(group.id)
            assert result is group

    def test_get_device_group_not_found(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_group_by_uuid.return_value = (
                True,
                None,
                None,
            )
            assert mgr.get_device_group("missing") is None

    def test_get_device_group_repo_error(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_group_by_uuid.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_device_group("x") is None

    def test_get_device_group_by_name_found(self):
        mgr = make_dg_manager()
        group = make_group(name="my-group")
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_group_by_name.return_value = (
                True,
                None,
                group,
            )
            assert mgr.get_device_group_by_name("my-group") is group

    def test_get_device_group_by_name_not_found(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_group_by_name.return_value = (
                True,
                None,
                None,
            )
            assert mgr.get_device_group_by_name("missing") is None

    def test_get_device_group_by_name_repo_error(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_group_by_name.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_device_group_by_name("err") is None

    def test_get_visible_device_group_found(self):
        mgr = make_dg_manager()
        group = make_group(is_public=False)
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_device_group_by_uuid.return_value = (
                True,
                None,
                group,
            )
            result = mgr.get_visible_device_group(
                group.id, project_id=group.project_id
            )
            assert result is group

    def test_get_visible_device_group_not_found(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_device_group_by_uuid.return_value = (
                True,
                None,
                None,
            )
            assert mgr.get_visible_device_group("x", project_id="p") is None

    def test_get_visible_device_group_repo_error(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_device_group_by_uuid.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_visible_device_group("x", project_id="p") is None


# ------------------------------------------------------------------ #
# DeviceGroupManager list methods
# ------------------------------------------------------------------ #
class TestDeviceGroupManagerList:
    """Tests for DeviceGroupManager list methods."""

    def test_get_device_groups_no_filter(self):
        mgr = make_dg_manager()
        g1 = make_group(name="a")
        g2 = make_group(name="b")
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_groups.return_value = (
                True,
                None,
                [g1, g2],
            )
            result = mgr.get_device_groups()
            assert len(result) == 2

    def test_get_device_groups_repo_failure(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_groups.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_device_groups() == []

    def test_get_device_groups_with_name_filter(self):
        mgr = make_dg_manager()
        g1 = make_group(name="a")
        g2 = make_group(name="b")
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_groups.return_value = (
                True,
                None,
                [g1, g2],
            )
            result = mgr.get_device_groups(filters={"group_name": "a"})
            assert len(result) == 1
            assert result[0].name == "a"

    def test_get_device_groups_with_ids_filter(self):
        """get_device_groups should pass group_ids as DB-level id filter."""
        mgr = make_dg_manager()
        g1 = make_group(name="a")
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_device_groups.return_value = (
                True,
                None,
                [g1],
            )
            result = mgr.get_device_groups(filters={"group_ids": [g1.id]})
            assert len(result) == 1
            # Verify DB-level filter was passed
            call_kwargs = mock_repo.get_device_groups.call_args.kwargs
            assert call_kwargs["filters"] == {"id": [g1.id]}

    def test_get_visible_device_groups_no_filter(self):
        mgr = make_dg_manager()
        g1 = make_group(name="a")
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_device_groups.return_value = (
                True,
                None,
                [g1],
            )
            result = mgr.get_visible_device_groups(project_id="p")
            assert len(result) == 1

    def test_get_visible_device_groups_repo_failure(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_device_groups.return_value = (
                False,
                "db error",
                None,
            )
            assert mgr.get_visible_device_groups(project_id="p") == []

    def test_get_visible_device_groups_with_name_filter(self):
        mgr = make_dg_manager()
        g1 = make_group(name="a")
        g2 = make_group(name="b")
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_device_groups.return_value = (
                True,
                None,
                [g1, g2],
            )
            result = mgr.get_visible_device_groups(
                filters={"group_name": "b"}, project_id="p"
            )
            assert len(result) == 1
            assert result[0].name == "b"

    def test_get_visible_device_groups_with_ids_filter(self):
        """get_visible_device_groups should filter by group_ids in-memory."""
        mgr = make_dg_manager()
        g1 = make_group(name="a")
        g2 = make_group(name="b")
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_visible_device_groups.return_value = (
                True,
                None,
                [g1, g2],
            )
            result = mgr.get_visible_device_groups(
                filters={"group_ids": [g1.id]}, project_id="p"
            )
            assert len(result) == 1
            assert str(result[0].id) == str(g1.id)


# ------------------------------------------------------------------ #
# DeviceGroupManager mutations
# ------------------------------------------------------------------ #
class TestDeviceGroupManagerMutations:
    """Tests for DeviceGroupManager create/update/delete."""

    def test_create_device_group(self):
        mgr = make_dg_manager()
        group = make_group()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.create_device_group.return_value = (
                True,
                None,
                group,
            )
            ok, err, result = mgr.create_device_group({"name": "x"})
            assert ok is True
            assert result is group

    def test_update_device_group(self):
        mgr = make_dg_manager()
        group = make_group()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.update_device_group.return_value = (
                True,
                None,
                group,
            )
            ok, err, result = mgr.update_device_group(
                group.id, {"name": "new"}, db_filters={}
            )
            assert ok is True
            assert result is group

    def test_delete_device_group(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_device_group.return_value = (True, None)
            ok, err = mgr.delete_device_group("id", db_filters={})
            assert ok is True

    def test_delete_device_group_failure(self):
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_device_group.return_value = (
                False,
                "not found",
            )
            ok, err = mgr.delete_device_group("id", db_filters={})
            assert ok is False

    def test_delete_device_groups_batch(self):
        """delete_device_groups should iterate and collect results."""
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_device_group.side_effect = [
                (True, None),
                (False, "not found"),
            ]
            results = mgr.delete_device_groups(["id1", "id2"], db_filters={})
            assert len(results) == 2
            assert results[0] == ("id1", True, None)
            assert results[1] == ("id2", False, "not found")

    def test_delete_device_groups_batch_all_success(self):
        """delete_device_groups should return all success when all pass."""
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.delete_device_group.return_value = (True, None)
            results = mgr.delete_device_groups(["id1", "id2"], db_filters={})
            assert len(results) == 2
            for gid, success, err in results:
                assert success is True
                assert err is None

    def test_delete_device_groups_blocked_by_flavor(self):
        """delete_device_groups blocks groups referenced by flavors."""
        mgr = make_dg_manager()
        group = make_group(group_id="gid1", name="blocked-group")
        flavor_mgr = MagicMock()
        flavor_mgr.get_flavor_ids_by_device_group.return_value = ["fid1"]
        mock_flavor = MagicMock()
        mock_flavor.name = "my-flavor"
        flavor_mgr.get_flavor.return_value = mock_flavor
        with patch.object(mgr, "get_device_group", return_value=group):
            with patch(
                "wy_qcos.device.device_group_manager.DeviceGroupRepository"
            ) as mock_repo_cls:
                results = mgr.delete_device_groups(
                    ["gid1"], flavor_manager=flavor_mgr
                )
                assert len(results) == 1
                assert results[0][0] == "gid1"
                assert results[0][1] is False
                assert "referenced by flavor" in results[0][2]
                # delete should NOT be called for blocked group
                mock_repo_cls.return_value.delete_device_group.assert_not_called()

    def test_delete_device_groups_partial_blocked_by_flavor(self):
        """delete_device_groups: one blocked, one deleted."""
        mgr = make_dg_manager()
        group1 = make_group(group_id="gid1", name="blocked-group")
        group2 = make_group(group_id="gid2", name="ok-group")
        flavor_mgr = MagicMock()
        # gid1 blocked, gid2 not referenced
        flavor_mgr.get_flavor_ids_by_device_group.side_effect = [
            ["fid1"],
            [],
        ]
        mock_flavor = MagicMock()
        mock_flavor.name = "my-flavor"
        flavor_mgr.get_flavor.return_value = mock_flavor
        with patch.object(
            mgr, "get_device_group", side_effect=[group1, group2]
        ):
            with patch(
                "wy_qcos.device.device_group_manager.DeviceGroupRepository"
            ) as mock_repo_cls:
                mock_repo_cls.return_value.delete_device_group.return_value = (
                    True,
                    None,
                )
                results = mgr.delete_device_groups(
                    ["gid1", "gid2"], flavor_manager=flavor_mgr
                )
                assert len(results) == 2
                assert results[0][1] is False
                assert results[1][1] is True
                # delete called only for gid2
                mock_repo_cls.return_value.delete_device_group.assert_called_once()

    def test_delete_device_groups_no_flavor_manager(self):
        """delete_device_groups skips flavor check when no flavor_manager."""
        mgr = make_dg_manager()
        with patch(
            "wy_qcos.device.device_group_manager.DeviceGroupRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.delete_device_group.return_value = (
                True,
                None,
            )
            results = mgr.delete_device_groups(["gid1"], flavor_manager=None)
            assert len(results) == 1
            assert results[0][1] is True


# ------------------------------------------------------------------ #
# DeviceGroupManager.get_device_names_by_group
# ------------------------------------------------------------------ #
class TestGetDeviceNamesByGroup:
    """Tests for get_device_names_by_group."""

    def test_empty_identifier(self):
        mgr = make_dg_manager()
        assert mgr.get_device_names_by_group("") == []

    def test_by_name(self):
        mgr = make_dg_manager()
        group = make_group(device_names=["dev1", "dev2"])
        with patch.object(mgr, "get_device_group_by_name", return_value=group):
            result = mgr.get_device_names_by_group("my-group")
            assert result == ["dev1", "dev2"]

    def test_by_uuid(self):
        mgr = make_dg_manager()
        gid = str(uuid.uuid4())
        group = make_group(group_id=gid, device_names=["dev3"])
        with patch.object(mgr, "get_device_group", return_value=group):
            result = mgr.get_device_names_by_group(gid)
            assert result == ["dev3"]

    def test_group_not_found(self):
        mgr = make_dg_manager()
        with patch.object(mgr, "get_device_group_by_name", return_value=None):
            result = mgr.get_device_names_by_group("missing")
            assert result == []

    def test_group_not_found_uuid(self):
        mgr = make_dg_manager()
        gid = str(uuid.uuid4())
        with patch.object(mgr, "get_device_group", return_value=None):
            result = mgr.get_device_names_by_group(gid)
            assert result == []

    def test_empty_device_names(self):
        mgr = make_dg_manager()
        group = make_group(device_names=[])
        with patch.object(mgr, "get_device_group_by_name", return_value=group):
            result = mgr.get_device_names_by_group("g")
            assert result == []


# ------------------------------------------------------------------ #
# DeviceGroupFilter
# ------------------------------------------------------------------ #
class TestDeviceGroupFilter:
    """Tests for DeviceGroupFilter."""

    def test_is_enabled_no_group_ref(self):
        f = DeviceGroupFilter()
        spec = make_spec(flavor_specs={})
        assert f.is_enabled(spec) is False

    def test_is_enabled_with_group_ref(self):
        f = DeviceGroupFilter()
        key = FlavorConstant.FS_KEY_GATE_DEVICE_GROUPS
        spec = make_spec(flavor_specs={key: "my-group"})
        assert f.is_enabled(spec) is True

    def test_filter_one_disabled(self):
        """When no group ref, all devices pass."""
        f = DeviceGroupFilter()
        spec = make_spec(flavor_specs={})
        ds = make_device_state("dummy")
        assert f._filter_one(ds, spec) is True

    def test_filter_one_no_manager(self):
        """When manager is None but filter enabled, pass."""
        f = DeviceGroupFilter()
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_GATE_DEVICE_GROUPS: "g"}
        )
        ds = make_device_state("dummy")
        assert f._filter_one(ds, spec) is True

    def test_filter_one_in_group(self):
        mock_mgr = MagicMock()
        mock_mgr.get_device_names_by_group.return_value = [
            "dummy",
            "qutip",
        ]
        f = DeviceGroupFilter()
        f.set_device_group_manager(mock_mgr)
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_GATE_DEVICE_GROUPS: "my-group"}
        )
        ds = make_device_state("dummy")
        assert f._filter_one(ds, spec) is True

    def test_filter_one_not_in_group(self):
        mock_mgr = MagicMock()
        mock_mgr.get_device_names_by_group.return_value = [
            "other",
        ]
        f = DeviceGroupFilter()
        f.set_device_group_manager(mock_mgr)
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_GATE_DEVICE_GROUPS: "my-group"}
        )
        ds = make_device_state("dummy")
        assert f._filter_one(ds, spec) is False

    def test_filter_one_empty_device_list(self):
        mock_mgr = MagicMock()
        mock_mgr.get_device_names_by_group.return_value = []
        f = DeviceGroupFilter()
        f.set_device_group_manager(mock_mgr)
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_GATE_DEVICE_GROUPS: "empty"}
        )
        ds = make_device_state("dummy")
        assert f._filter_one(ds, spec) is False

    def test_set_device_group_manager(self):
        f = DeviceGroupFilter()
        mock_mgr = MagicMock()
        f.set_device_group_manager(mock_mgr)
        assert f._device_group_manager is mock_mgr


# ------------------------------------------------------------------ #
# API route: create_device_group
# ------------------------------------------------------------------ #
class TestCreateDeviceGroupRoute:
    """Tests for create_device_group API route."""

    def _make_request(self, **kwargs):
        defaults = {
            "name": "new-group",
            "description": "desc",
            "is_public": True,
            "device_names": ["dev1"],
        }
        defaults.update(kwargs)
        return schemas.CreateDeviceGroupRequest(**defaults)

    def test_create_success(self):
        group = make_group(name="new-group")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.create_device_group.return_value = (True, None, group)
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request()
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group."
                "get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = create_device_group(body, mock_request, auth_data=None)
            assert result.name == "new-group"

    def test_create_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_device_group_manager.return_value = None
        body = self._make_request()
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                create_device_group(body, MagicMock(), auth_data=None)

    def test_create_empty_name(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(name="")
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group."
                "get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_device_group(body, mock_request, auth_data=None)

    def test_create_duplicate_name(self):
        existing = make_group(name="dup")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = [existing]
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(name="dup")
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group."
                "get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_device_group(body, mock_request, auth_data=None)

    def test_create_project_not_found(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(
            project_id="00000000-0000-4000-8000-000000000099"
        )
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = None
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group."
                "get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_device_group(body, mock_request, auth_data=None)

    def test_create_repo_failure(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.create_device_group.return_value = (
            False,
            "db error",
            None,
        )
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request()
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group."
                "get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                create_device_group(body, mock_request, auth_data=None)

    def test_create_with_auth_project_id(self):
        group = make_group(name="new-group")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.create_device_group.return_value = (True, None, group)
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request()
        mock_request = MagicMock()
        mock_project_mgr = MagicMock()
        mock_project_mgr.get_project_by_id.return_value = MagicMock()
        auth_data = {"project_id": Constant.ADMIN_PROJECT_ID}
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group."
                "get_project_manager",
                return_value=mock_project_mgr,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = create_device_group(
                body, mock_request, auth_data=auth_data
            )
            assert result.name == "new-group"


# ------------------------------------------------------------------ #
# API route: update_device_group
# ------------------------------------------------------------------ #
class TestUpdateDeviceGroupRoute:
    """Tests for update_device_group API route."""

    def _make_request(self, group_id, **kwargs):
        return schemas.UpdateDeviceGroupRequest(group_id=group_id, **kwargs)

    def test_update_success(self):
        gid = str(uuid.uuid4())
        updated = make_group(group_id=gid, name="updated")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.update_device_group.return_value = (True, None, updated)
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(gid, name="updated")
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = update_device_group(body, MagicMock(), auth_data=None)
            assert result.name == "updated"

    def test_update_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_device_group_manager.return_value = None
        body = self._make_request(str(uuid.uuid4()), name="x")
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                update_device_group(body, MagicMock(), auth_data=None)

    def test_update_no_fields(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(str(uuid.uuid4()))
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_device_group(body, MagicMock(), auth_data=None)

    def test_update_duplicate_name(self):
        gid = str(uuid.uuid4())
        other = make_group(name="taken")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = [other]
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(gid, name="taken")
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_device_group(body, MagicMock(), auth_data=None)

    def test_update_project_not_found(self):
        gid = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(
            gid,
            project_id="00000000-0000-4000-8000-000000000099",
        )
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group."
                "get_project_manager",
                return_value=MagicMock(),
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_device_group(body, MagicMock(), auth_data=None)

    def test_update_repo_failure(self):
        gid = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.update_device_group.return_value = (
            False,
            "db error",
            None,
        )
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(gid, name="x")
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            with pytest.raises(Exception):
                update_device_group(body, MagicMock(), auth_data=None)

    def test_update_device_names(self):
        gid = str(uuid.uuid4())
        updated = make_group(group_id=gid, device_names=["dev1", "dev2"])
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.update_device_group.return_value = (True, None, updated)
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(gid, device_names=["dev1", "dev2"])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = update_device_group(body, MagicMock(), auth_data=None)
            assert result is not None

    def test_update_clear_description(self):
        """Explicitly passing description=None clears the field."""
        gid = str(uuid.uuid4())
        updated = make_group(group_id=gid, description=None)
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.update_device_group.return_value = (True, None, updated)
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(gid, description=None)
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = update_device_group(body, MagicMock(), auth_data=None)
            assert result is not None
            call_data = mgr.update_device_group.call_args[0][1]
            assert call_data["description"] is None

    def test_update_clear_device_names(self):
        """Explicitly passing device_names=None clears the field."""
        gid = str(uuid.uuid4())
        updated = make_group(group_id=gid, device_names=None)
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = []
        mgr.update_device_group.return_value = (True, None, updated)
        mock_sched.get_device_group_manager.return_value = mgr
        body = self._make_request(gid, device_names=None)
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = update_device_group(body, MagicMock(), auth_data=None)
            assert result is not None
            call_data = mgr.update_device_group.call_args[0][1]
            assert call_data["device_names"] is None


# ------------------------------------------------------------------ #
# API route: get_device_group / get_device_groups
# ------------------------------------------------------------------ #
class TestGetDeviceGroupRoute:
    """Tests for get_device_group and get_device_groups routes."""

    def test_get_device_group_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_device_group_manager.return_value = None
        body = schemas.GetDeviceGroupRequest(group_id=str(uuid.uuid4()))
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                get_device_group(body, auth_data=None)

    def test_get_device_group_super_admin(self):
        group = make_group()
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_group.return_value = group
        mock_sched.get_device_group_manager.return_value = mgr
        body = schemas.GetDeviceGroupRequest(group_id=group.id)
        auth_data = {"is_super_admin": True}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            result = get_device_group(body, auth_data=auth_data)
            assert result.name == group.name

    def test_get_device_group_non_admin_visible(self):
        group = make_group()
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_visible_device_group.return_value = group
        mock_sched.get_device_group_manager.return_value = mgr
        body = schemas.GetDeviceGroupRequest(group_id=group.id)
        auth_data = {"is_super_admin": False, "project_id": "p"}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            result = get_device_group(body, auth_data=auth_data)
            assert result.name == group.name

    def test_get_device_group_not_found(self):
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_group.return_value = None
        mock_sched.get_device_group_manager.return_value = mgr
        body = schemas.GetDeviceGroupRequest(group_id=str(uuid.uuid4()))
        auth_data = {"is_super_admin": True}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                get_device_group(body, auth_data=auth_data)

    def test_get_device_groups_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_device_group_manager.return_value = None
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                get_device_groups(body=None, auth_data=None)

    def test_get_device_groups_super_admin(self):
        g1 = make_group(name="a")
        g2 = make_group(name="b")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_device_groups.return_value = [g1, g2]
        mock_sched.get_device_group_manager.return_value = mgr
        auth_data = {"is_super_admin": True}
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            result = get_device_groups(body=None, auth_data=auth_data)
            assert len(result) == 2

    def test_get_device_groups_non_admin(self):
        g1 = make_group(name="a")
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.get_visible_device_groups.return_value = [g1]
        mock_sched.get_device_group_manager.return_value = mgr
        auth_data = {"is_super_admin": False, "project_id": "p"}
        body = schemas.GetDeviceGroupsRequest(filters={"group_name": "a"})
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            result = get_device_groups(body=body, auth_data=auth_data)
            assert len(result) == 1


# ------------------------------------------------------------------ #
# API route: delete_device_groups (batch)
# ------------------------------------------------------------------ #
class TestDeleteDeviceGroupsRoute:
    """Tests for delete_device_groups route."""

    def test_delete_no_manager(self):
        mock_sched = MagicMock()
        mock_sched.get_device_group_manager.return_value = None
        body = schemas.DeleteDeviceGroupsRequest(group_ids=[str(uuid.uuid4())])
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
            mock_sched,
        ):
            with pytest.raises(Exception):
                delete_device_groups(body, auth_data=None)

    def test_delete_success(self):
        gid = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_device_groups.return_value = [(gid, True, None)]
        mock_sched.get_device_group_manager.return_value = mgr
        flavor_mgr = MagicMock()
        mock_sched.get_flavor_manager.return_value = flavor_mgr
        body = schemas.DeleteDeviceGroupsRequest(group_ids=[gid])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = delete_device_groups(body, auth_data=None)
            assert len(result.results) == 1
            assert str(result.results[0].group_id) == gid
            assert result.results[0].success is True

    def test_delete_failure(self):
        """Batch delete should return failure result, not raise."""
        gid = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_device_groups.return_value = [
            (gid, False, "not found"),
        ]
        mock_sched.get_device_group_manager.return_value = mgr
        flavor_mgr = MagicMock()
        mock_sched.get_flavor_manager.return_value = flavor_mgr
        body = schemas.DeleteDeviceGroupsRequest(group_ids=[gid])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = delete_device_groups(body, auth_data=None)
            assert len(result.results) == 1
            assert result.results[0].success is False
            assert "not found" in result.results[0].error

    def test_delete_blocked_by_flavor_reference(self):
        """Batch delete should mark blocked groups as failed.

        Flavor reference check is now done in the manager layer;
        the route simply forwards the manager's per-group result.
        """
        gid = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_device_groups.return_value = [
            (
                gid,
                False,
                "Device group 'referenced-group' is referenced by "
                "flavor(s): my-flavor. Must remove the device group "
                "from the flavor(s) before deleting the device group.",
            ),
        ]
        mock_sched.get_device_group_manager.return_value = mgr
        flavor_mgr = MagicMock()
        mock_sched.get_flavor_manager.return_value = flavor_mgr
        body = schemas.DeleteDeviceGroupsRequest(group_ids=[gid])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = delete_device_groups(body, auth_data=None)
            assert len(result.results) == 1
            assert result.results[0].success is False
            assert "referenced" in result.results[0].error

    def test_delete_partial_blocked(self):
        """Batch delete: one blocked, one success, both in results.

        Flavor reference check is now in the manager layer; the
        route receives the manager's per-group results directly.
        """
        gid1 = str(uuid.uuid4())
        gid2 = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_device_groups.return_value = [
            (gid1, False, "referenced by flavor"),
            (gid2, True, None),
        ]
        mock_sched.get_device_group_manager.return_value = mgr
        flavor_mgr = MagicMock()
        mock_sched.get_flavor_manager.return_value = flavor_mgr

        body = schemas.DeleteDeviceGroupsRequest(group_ids=[gid1, gid2])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = delete_device_groups(body, auth_data=None)
            assert len(result.results) == 2
            assert result.results[0].success is False
            assert result.results[1].success is True

    def test_delete_success_no_flavor_manager(self):
        """Delete succeeds when flavor manager is not initialized."""
        gid = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_device_groups.return_value = [(gid, True, None)]
        mock_sched.get_device_group_manager.return_value = mgr
        mock_sched.get_flavor_manager.return_value = None
        body = schemas.DeleteDeviceGroupsRequest(group_ids=[gid])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = delete_device_groups(body, auth_data=None)
            assert len(result.results) == 1
            assert str(result.results[0].group_id) == gid
            assert result.results[0].success is True

    def test_delete_dedup(self):
        """Duplicate group_ids should be deduplicated in the route."""
        gid = str(uuid.uuid4())
        mock_sched = MagicMock()
        mgr = MagicMock()
        mgr.delete_device_groups.return_value = [(gid, True, None)]
        mock_sched.get_device_group_manager.return_value = mgr
        flavor_mgr = MagicMock()
        mock_sched.get_flavor_manager.return_value = flavor_mgr
        body = schemas.DeleteDeviceGroupsRequest(group_ids=[gid, gid])
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.get_db_filters",
                return_value={},
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.device_group.scheduler",
                mock_sched,
            ),
        ):
            result = delete_device_groups(body, auth_data=None)
            assert len(result.results) == 1
        # manager's delete_device_groups should be called with
        # the deduplicated list (single entry)
        call_args = mgr.delete_device_groups.call_args.args
        assert call_args[0] == [gid]


# ------------------------------------------------------------------ #
# DeviceGroupRepository (using mocks)
# ------------------------------------------------------------------ #
class TestDeviceGroupRepository:
    """Tests for DeviceGroupRepository using mocks."""

    @pytest.fixture
    def repo_setup(self):
        from wy_qcos.db.repositories.device_group import (
            DeviceGroupRepository,
        )

        mock_session = MagicMock()
        repo = DeviceGroupRepository(mock_session)
        return repo, mock_session

    def test_create_success(self, repo_setup):
        repo, session = repo_setup
        data = {
            "id": str(uuid.uuid4()),
            "name": "test",
            "project_id": Constant.ADMIN_PROJECT_ID,
        }
        ok, err, group = repo.create_device_group(data)
        assert ok is True
        session.add.assert_called_once()
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

    def test_create_failure(self, repo_setup):
        repo, session = repo_setup
        session.commit.side_effect = Exception("db error")
        data = {
            "id": str(uuid.uuid4()),
            "name": "fail",
            "project_id": Constant.ADMIN_PROJECT_ID,
        }
        ok, err, group = repo.create_device_group(data)
        assert ok is False
        assert "db error" in err
        session.rollback.assert_called_once()

    def test_get_by_uuid(self, repo_setup):
        repo, _ = repo_setup
        group = make_group()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, group)
        ):
            ok, err, result = repo.get_device_group_by_uuid(group.id)
        assert ok is True
        assert result is group

    def test_get_by_uuid_not_found(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err, result = repo.get_device_group_by_uuid("x")
        assert ok is True
        assert result is None

    def test_get_by_name(self, repo_setup):
        repo, _ = repo_setup
        group = make_group(name="by-name")
        with patch.object(
            repo, "get_by_attr", return_value=(True, None, group)
        ):
            ok, err, result = repo.get_device_group_by_name("by-name")
        assert ok is True
        assert result is group

    def test_get_visible_by_uuid_found(self, repo_setup):
        repo, session = repo_setup
        group = make_group(is_public=True)
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = group
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result
        ok, err, result = repo.get_visible_device_group_by_uuid(
            group.id, project_id="other"
        )
        assert ok is True
        assert result is group

    def test_get_visible_by_uuid_not_found(self, repo_setup):
        repo, session = repo_setup
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result
        ok, err, result = repo.get_visible_device_group_by_uuid(
            "x", project_id="other"
        )
        assert ok is True
        assert result is None

    def test_get_visible_by_uuid_error(self, repo_setup):
        repo, session = repo_setup
        session.execute.side_effect = Exception("db error")
        ok, err, result = repo.get_visible_device_group_by_uuid(
            "x", project_id="other"
        )
        assert ok is False
        assert "db error" in err

    def test_get_visible_groups_success(self, repo_setup):
        repo, session = repo_setup
        g1 = make_group(name="a")
        g2 = make_group(name="b")
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [g1, g2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result
        ok, err, groups = repo.get_visible_device_groups(project_id="p")
        assert ok is True
        assert len(groups) == 2

    def test_get_visible_groups_error(self, repo_setup):
        repo, session = repo_setup
        session.execute.side_effect = Exception("db error")
        ok, err, groups = repo.get_visible_device_groups(project_id="p")
        assert ok is False

    def test_get_all(self, repo_setup):
        repo, _ = repo_setup
        g1 = make_group(name="all-1")
        with patch.object(repo, "get_all", return_value=(True, None, [g1])):
            ok, err, groups = repo.get_device_groups()
        assert ok is True
        assert len(groups) == 1

    def test_delete_success(self, repo_setup):
        repo, session = repo_setup
        group = make_group()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, group)
        ):
            ok, err = repo.delete_device_group(group.id)
        assert ok is True
        session.delete.assert_called_once_with(group)

    def test_delete_not_found(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err = repo.delete_device_group("missing")
        assert ok is False
        assert "not found" in err

    def test_delete_exception(self, repo_setup):
        repo, session = repo_setup
        group = make_group()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, group)
        ):
            session.delete.side_effect = Exception("delete error")
            ok, err = repo.delete_device_group(group.id)
        assert ok is False
        session.rollback.assert_called_once()

    def test_update_success(self, repo_setup):
        repo, session = repo_setup
        group = make_group(description="old")
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, group)
        ):
            ok, err, result = repo.update_device_group(
                group.id, {"description": "new"}
            )
        assert ok is True
        assert group.description == "new"
        session.commit.assert_called_once()

    def test_update_not_found(self, repo_setup):
        repo, _ = repo_setup
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, None)
        ):
            ok, err, result = repo.update_device_group(
                "missing", {"name": "x"}
            )
        assert ok is False
        assert "not found" in err

    def test_update_exception(self, repo_setup):
        repo, session = repo_setup
        group = make_group()
        with patch.object(
            repo, "get_by_uuid", return_value=(True, None, group)
        ):
            session.commit.side_effect = Exception("commit error")
            ok, err, result = repo.update_device_group(group.id, {"name": "x"})
        assert ok is False
        session.rollback.assert_called_once()


# ------------------------------------------------------------------ #
# DeviceGroupNotFoundError
# ------------------------------------------------------------------ #
class TestDeviceGroupNotFoundError:
    """Tests for DeviceGroupNotFoundError."""

    def test_error_attributes(self):
        err = DeviceGroupNotFoundError("test message")
        assert err.module_name == "DeviceGroup"
        assert err.error_code == -301
        assert err.err_type == "DeviceGroupNotFoundError"
        assert "test message" in err.message

    def test_error_get_msgs(self):
        err = DeviceGroupNotFoundError("not found")
        msgs = err.get_err_msgs()
        assert "[DeviceGroup]" in msgs
        assert "DeviceGroupNotFoundError" in msgs

    def test_error_is_base_exception(self):
        from wy_qcos.common.errors import BaseException

        err = DeviceGroupNotFoundError("x")
        assert isinstance(err, BaseException)
        assert isinstance(err, Exception)


# ------------------------------------------------------------------ #
# DeviceGroup model
# ------------------------------------------------------------------ #
class TestDeviceGroupModel:
    """Tests for DeviceGroup model."""

    def test_table_name(self):
        assert DeviceGroup.__tablename__ == "device_groups"

    def test_columns(self):
        cols = {c.name for c in DeviceGroup.__table__.columns}
        expected = {
            "id",
            "project_id",
            "name",
            "description",
            "device_names",
            "is_public",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(cols)
