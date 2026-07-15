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

import logging
from typing import Any

from fastapi import Depends, Request

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import (
    errors as jsonrpc_errors,
)
from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    auth,
)
from wy_qcos.api.posiq.routes_jsonrpc.project import (
    get_project_manager,
)
from wy_qcos.api.posiq.routes_jsonrpc.routes import job_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.utils.db_utils import get_db_filters
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
module_name = "DEVICE_GROUP"


def _is_super_admin(auth_data: dict | None) -> bool:
    """Check if the caller is a super admin."""
    if not auth_data:
        return False
    return auth_data.get("is_super_admin", False)


def _current_project_id(auth_data: dict | None):
    """Get caller's project id from auth data."""
    return auth_data.get("project_id") if auth_data else None


def _validate_device_names(device_names: list[str] | None):
    """Validate device names exist, warn for non-existent ones.

    Checks each device name against the device manager. Logs a
    warning for devices that do not exist, but does not block
    the operation (allows adding non-existent devices).

    Args:
        device_names: list of device names to validate
    """
    if not device_names:
        return
    device_manager = scheduler.get_device_manager()
    if device_manager is None:
        return
    for name in device_names:
        # skip special value _all
        if name == "_all":
            continue
        if device_manager.get_device(name) is None:
            logger.warning(
                f"Device '{name}' does not exist, adding to group anyway"
            )


@job_api_v1.method(
    tags=["device_group"],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.BadRequestError],
)
def create_device_group(
    body: schemas.CreateDeviceGroupRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeviceGroupResponse:
    """Create a device group.

    Args:
        body: create device group request
        request: request object
        auth_data: authentication data

    Returns:
        device group response
    """
    func_name = "create_device_group"
    logger.info(f"Call {func_name}: {body.name}")

    device_group_manager = scheduler.get_device_group_manager()
    if device_group_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, "Device group manager not initialized"),
        )

    # Default project_id to current user's project_id if not provided
    if body.project_id is None and auth_data:
        project_id = auth_data.get("project_id")
        if project_id:
            body.project_id = project_id

    # Validate project_id exists in projects table
    project_manager = get_project_manager(request)
    project_id_str = str(body.project_id)
    project = project_manager.get_project_by_id(project_id_str)
    if project is None:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Failed to create device group: "
                f"project: {project_id_str} not exists",
            ),
        )

    # validate name
    if not body.name:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, "device group name is required"),
        )
    success, err_msg = Library.validate_name(body.name)
    if not success:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, err_msg),
        )

    # check duplicate name
    filters = {"group_name": body.name}
    device_groups = device_group_manager.get_device_groups(filters=filters)
    for device_group in device_groups:
        if device_group.name == body.name:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (
                    False,
                    f"Device group name already exists: {body.name}",
                ),
            )

    # validate device names (warn for non-existent devices)
    _seen = set()
    device_names = []
    for x in body.device_names:
        if x not in _seen:
            _seen.add(x)
            device_names.append(x)
    if "_all" in device_names:
        device_names = ["_all"]
    _validate_device_names(device_names)

    group_data: dict[str, Any] = {
        "name": body.name,
        "description": body.description,
        "device_names": device_names,
        "is_public": body.is_public,
        "project_id": str(body.project_id),
        "created_at": Library.get_current_datetime(),
        "updated_at": Library.get_current_datetime(),
    }

    success, error, group = device_group_manager.create_device_group(
        group_data
    )
    if not success or group is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, f"Failed to create device group: {error}"),
        )

    response = schemas.DeviceGroupResponse.model_validate(group)
    return response


@job_api_v1.method(
    tags=["device_group"],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.BadRequestError],
)
def update_device_group(
    body: schemas.UpdateDeviceGroupRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeviceGroupResponse:
    """Update a device group by ID.

    Args:
        body: update device group request
        request: request object
        auth_data: authentication data

    Returns:
        device group response
    """
    func_name = "update_device_group"
    logger.info(f"Call {func_name}: {body.group_id}")

    device_group_manager = scheduler.get_device_group_manager()
    if device_group_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, "Device group manager not initialized"),
        )

    # Apply project/user permission scoping
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )

    # build update data from non-None fields
    group_data: dict[str, Any] = {}
    if body.name is not None:
        success, err_msg = Library.validate_name(body.name)
        if not success:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, err_msg),
            )
        # check duplicate name
        filters = {"group_name": body.name}
        device_groups = device_group_manager.get_device_groups(filters=filters)
        for device_group in device_groups:
            if (
                device_group.name == body.name
                and device_group.id != body.group_id
            ):
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    (
                        False,
                        f"Device group name already exists: {body.name}",
                    ),
                )
        group_data["name"] = body.name
    if body.description is not None:
        group_data["description"] = body.description
    if body.is_public is not None:
        group_data["is_public"] = body.is_public
    if body.device_names is not None:
        _seen = set()
        device_names = []
        for x in body.device_names:
            if x not in _seen:
                _seen.add(x)
                device_names.append(x)
        if "_all" in device_names:
            device_names = ["_all"]
        _validate_device_names(device_names)
        group_data["device_names"] = device_names
    if body.project_id is not None:
        # Validate project_id exists in projects table
        project_manager = get_project_manager(request)
        project_id_str = str(body.project_id)
        project = project_manager.get_project_by_id(project_id_str)
        if project is None:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (
                    False,
                    f"Failed to update device group: "
                    f"project: {project_id_str} not exists",
                ),
            )
        group_data["project_id"] = project_id_str

    if not group_data:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, "No fields to update"),
        )

    group_data["updated_at"] = Library.get_current_datetime()

    success, error, group = device_group_manager.update_device_group(
        str(body.group_id), group_data, db_filters=db_filters
    )
    if not success or group is None:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, f"Failed to update device group: {error}"),
        )

    response = schemas.DeviceGroupResponse.model_validate(group)
    return response


@job_api_v1.method(
    tags=["device_group"],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.BadRequestError],
)
def get_device_group(
    body: schemas.GetDeviceGroupRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeviceGroupResponse:
    """Get a device group by ID.

    Args:
        body: get device group request
        auth_data: authentication data

    Returns:
        device group response
    """
    func_name = "get_device_group"
    logger.info(f"Call {func_name}: {body.group_id}")

    device_group_manager = scheduler.get_device_group_manager()
    if device_group_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, "Device group manager not initialized"),
        )
    # Visibility scoping
    if _is_super_admin(auth_data):
        group = device_group_manager.get_device_group(str(body.group_id))
    else:
        group = device_group_manager.get_visible_device_group(
            str(body.group_id),
            project_id=_current_project_id(auth_data),
        )
    if group is None:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, f"Device group not found: {body.group_id}"),
        )

    response = schemas.DeviceGroupResponse.model_validate(group)
    return response


@job_api_v1.method(
    tags=["device_group"],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.BadRequestError],
)
def get_device_groups(
    body: schemas.GetDeviceGroupsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> list[schemas.DeviceGroupResponse]:
    """Get all device groups with optional filtering.

    Args:
        body: get device groups request with optional filter dict
        auth_data: authentication data

    Returns:
        list of device group responses
    """
    func_name = "get_device_groups"
    logger.info(f"Call {func_name}: {body}")

    device_group_manager = scheduler.get_device_group_manager()
    if device_group_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, "Device group manager not initialized"),
        )
    filter_conditions = None
    if body:
        filter_conditions = body.filters
    if _is_super_admin(auth_data):
        groups = device_group_manager.get_device_groups(
            filters=filter_conditions
        )
    else:
        groups = device_group_manager.get_visible_device_groups(
            filters=filter_conditions,
            project_id=_current_project_id(auth_data),
        )
    return [schemas.DeviceGroupResponse.model_validate(g) for g in groups]


@job_api_v1.method(
    tags=["device_group"],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.BadRequestError],
)
def delete_device_groups(
    body: schemas.DeleteDeviceGroupsRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeleteDeviceGroupsResponse:
    """Delete multiple device groups by IDs (batch).

    Iterates over each group_id, checks flavor references, deletes
    it independently, and collects per-group results. Does not abort
    on individual failures.

    Args:
        body: delete device groups request (group_ids list)
        auth_data: authentication data

    Returns:
        delete device groups response with per-group results
    """
    func_name = "delete_device_groups"
    logger.info(f"Call {func_name}: {body.group_ids}")

    device_group_manager = scheduler.get_device_group_manager()
    if device_group_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, "Device group manager not initialized"),
        )
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )
    flavor_manager = scheduler.get_flavor_manager()

    # Deduplicate group_ids preserving order
    raw_ids = list(dict.fromkeys(str(gid) for gid in body.group_ids))
    results_data = device_group_manager.delete_device_groups(
        raw_ids,
        db_filters=db_filters,
        flavor_manager=flavor_manager,
    )
    results = [
        schemas.DeleteDeviceGroupResponseItem(group_id=gid, success=s, error=e)
        for gid, s, e in results_data
    ]
    return schemas.DeleteDeviceGroupsResponse(results=results)
