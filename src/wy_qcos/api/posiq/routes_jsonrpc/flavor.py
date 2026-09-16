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
import uuid
from typing import Any

from fastapi import Depends, Request

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    auth,
)
from wy_qcos.api.posiq.routes_jsonrpc.project import get_project_manager
from wy_qcos.api.posiq.routes_jsonrpc.routes import flavor_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.utils.db_utils import get_db_filters
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
module_name = "FLAVOR"


def _is_super_admin(auth_data: dict | None) -> bool:
    """Check if the caller is a super admin."""
    if not auth_data:
        return False
    return auth_data.get("is_super_admin", False)


def _validate_gate_fidelity(value, param_name: str):
    """Validate gate fidelity is in [0, 1] range.

    Args:
        value: fidelity value (None skips validation)
        param_name: parameter name for error message

    Returns:
        error message string or None if valid
    """
    if value is None:
        return None
    if value < 0 or value > 1:
        return f"{param_name} must be between 0 and 1 (inclusive), got {value}"
    return None


def _validate_qubits_range(min_qubits, max_qubits):
    """Validate min_qubits <= max_qubits (None excluded).

    Args:
        min_qubits: minimum qubits value
        max_qubits: maximum qubits value

    Returns:
        error message string or None if valid
    """
    if min_qubits is not None and max_qubits is not None:
        if min_qubits > max_qubits:
            return (
                f"min_qubits ({min_qubits}) must be less than "
                f"or equal to max_qubits ({max_qubits})"
            )
    return None


def _current_project_id(auth_data: dict | None):
    """Get caller's project id from auth data."""
    return auth_data.get("project_id") if auth_data else None


@flavor_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.ConflictError,
        jsonrpc_errors.InternalServerError,
    ],
)
def create_flavor(
    body: schemas.CreateFlavorRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.FlavorResponse:
    """Create a flavor (preset scheduling policy).

    Args:
        body: create flavor request
        request: request object
        auth_data: authentication data

    Returns:
        flavor response
    """
    func_name = "create_flavor"
    logger.info(f"Call {func_name}: {body.name}")

    flavor_manager = scheduler.get_flavor_manager()
    if flavor_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Flavor manager not initialized")
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
                f"Failed to create flavor: "
                f"project: {project_id_str} not exists",
            ),
        )

    # validate name
    if not body.name:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, "flavor name is required")
        )
    success, err_msg = Library.validate_name(body.name)
    if not success:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, err_msg)
        )

    # check duplicate name
    filters = {"flavor_name": body.name}
    flavors = flavor_manager.get_flavors(filters=filters)
    for flavor in flavors:
        if flavor.name == body.name:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, f"Flavor name already exists: {body.name}"),
            )

    # validate extra_properties via flavor_manager
    extra_properties = body.extra_properties
    ok, err = flavor_manager.validate_extra_properties(extra_properties)
    if not ok:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, err)
        )

    # validate device_groups (required, at least one)
    device_group_ids = [str(dg) for dg in body.device_groups]
    device_group_manager = scheduler.get_device_group_manager()
    ok, err = flavor_manager.validate_device_groups(
        device_group_ids, device_group_manager
    )
    if not ok:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, err)
        )

    # Validate qubits range and gate fidelity
    err = _validate_qubits_range(body.min_qubits, body.max_qubits)
    if err:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, err)
        )
    err = _validate_gate_fidelity(
        body.gate_fidelity_1q_min, "gate_fidelity_1q_min"
    )
    if err:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, err)
        )
    err = _validate_gate_fidelity(
        body.gate_fidelity_2q_min, "gate_fidelity_2q_min"
    )
    if err:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, err)
        )

    flavor_data: dict[str, Any] = {
        "name": body.name,
        "description": body.description,
        "is_public": body.is_public,
        "project_id": str(body.project_id),
        "min_qubits": body.min_qubits,
        "max_qubits": body.max_qubits,
        "gate_fidelity_1q_min": body.gate_fidelity_1q_min,
        "gate_fidelity_2q_min": body.gate_fidelity_2q_min,
        "extra_properties": extra_properties,
        "device_groups": device_group_ids,
        "created_at": Library.get_current_datetime(),
        "updated_at": Library.get_current_datetime(),
    }

    success, error, flavor = flavor_manager.create_flavor(flavor_data)
    if not success or flavor is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, f"Failed to create flavor: {error}"),
        )

    # Build response with device_groups from mapping table
    response = schemas.FlavorResponse.model_validate(flavor)
    response.device_groups = [
        uuid.UUID(dg_id)
        for dg_id in flavor_manager.get_flavor_device_groups(str(flavor.id))
    ]
    return response


@flavor_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.ConflictError,
        jsonrpc_errors.InternalServerError,
    ],
)
def update_flavor(
    body: schemas.UpdateFlavorRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.FlavorResponse:
    """Update a flavor by ID.

    Args:
        body: update flavor request
        request: request object
        auth_data: authentication data

    Returns:
        flavor response
    """
    func_name = "update_flavor"
    logger.info(f"Call {func_name}: {body.flavor_id}")

    flavor_manager = scheduler.get_flavor_manager()
    if flavor_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Flavor manager not initialized")
        )

    # Apply project/user permission scoping
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )

    # Determine which fields were explicitly provided (set) in the
    # request. model_fields_set distinguishes "omitted" (not set,
    # do not touch) from "explicitly None" (clear the field).
    set_fields = body.model_fields_set

    # build update data from explicitly-provided fields only
    flavor_data: dict[str, Any] = {}
    if "name" in set_fields and body.name is not None:
        success, err_msg = Library.validate_name(body.name)
        if not success:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, err_msg),
            )
        # check duplicate name
        filters = {"flavor_name": body.name}
        flavors = flavor_manager.get_flavors(filters=filters)
        for flavor in flavors:
            if flavor.name == body.name and flavor.id != body.flavor_id:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    f"Flavor name already exists: {body.name}",
                )
        flavor_data["name"] = body.name
    if "description" in set_fields:
        flavor_data["description"] = body.description
    if "is_public" in set_fields and body.is_public is not None:
        flavor_data["is_public"] = body.is_public
    if "project_id" in set_fields and body.project_id is not None:
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
                    f"Failed to update flavor: "
                    f"project: {project_id_str} not exists",
                ),
            )
        flavor_data["project_id"] = project_id_str

    if "min_qubits" in set_fields:
        flavor_data["min_qubits"] = body.min_qubits
    if "max_qubits" in set_fields:
        flavor_data["max_qubits"] = body.max_qubits
    if "gate_fidelity_1q_min" in set_fields:
        flavor_data["gate_fidelity_1q_min"] = body.gate_fidelity_1q_min
    if "gate_fidelity_2q_min" in set_fields:
        flavor_data["gate_fidelity_2q_min"] = body.gate_fidelity_2q_min

    # Validate qubits range and gate fidelity
    # (use new value if provided, else existing value)
    existing_flavor = flavor_manager.get_flavor(str(body.flavor_id))
    if existing_flavor is not None:
        effective_min_qubits = (
            body.min_qubits
            if "min_qubits" in set_fields
            else existing_flavor.min_qubits
        )
        effective_max_qubits = (
            body.max_qubits
            if "max_qubits" in set_fields
            else existing_flavor.max_qubits
        )
        err = _validate_qubits_range(
            effective_min_qubits, effective_max_qubits
        )
        if err:
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, err)
            )
    # validate gate fidelity only if a value is provided
    if (
        "gate_fidelity_1q_min" in set_fields
        and body.gate_fidelity_1q_min is not None
    ):
        err = _validate_gate_fidelity(
            body.gate_fidelity_1q_min, "gate_fidelity_1q_min"
        )
        if err:
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, err)
            )
    if (
        "gate_fidelity_2q_min" in set_fields
        and body.gate_fidelity_2q_min is not None
    ):
        err = _validate_gate_fidelity(
            body.gate_fidelity_2q_min, "gate_fidelity_2q_min"
        )
        if err:
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, err)
            )

    # extra_properties: merge if a dict is provided, clear if
    # None is provided, keep existing if omitted
    if "extra_properties" in set_fields:
        if body.extra_properties is None:
            # clear all extra_properties
            flavor_data["extra_properties"] = None
        else:
            # validate extra_properties via flavor_manager
            ok, err = flavor_manager.validate_extra_properties(
                body.extra_properties
            )
            if not ok:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name, func_name, (False, err)
                )
            if existing_flavor is None:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    (False, f"Flavor not found: {body.flavor_id}"),
                )
            merged_extra = dict(existing_flavor.extra_properties or {})
            merged_extra.update(body.extra_properties)
            flavor_data["extra_properties"] = merged_extra

    # device_groups: replace if a list is provided, clear if
    # None is provided, keep existing if omitted
    if "device_groups" in set_fields:
        if body.device_groups is None:
            # clear all device group mappings
            flavor_data["device_groups"] = []
        else:
            device_group_ids = [str(dg) for dg in body.device_groups]
            device_group_manager = scheduler.get_device_group_manager()
            ok, err = flavor_manager.validate_device_groups(
                device_group_ids, device_group_manager
            )
            if not ok:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name, func_name, (False, err)
                )
            flavor_data["device_groups"] = device_group_ids

    flavor_data["updated_at"] = Library.get_current_datetime()

    success, error, flavor = flavor_manager.update_flavor(
        str(body.flavor_id), flavor_data, db_filters=db_filters
    )
    if not success or flavor is None:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, f"Failed to update flavor: {error}"),
        )

    # Build response with device_groups from mapping table
    response = schemas.FlavorResponse.model_validate(flavor)
    response.device_groups = [
        uuid.UUID(dg_id)
        for dg_id in flavor_manager.get_flavor_device_groups(str(flavor.id))
    ]
    return response


@flavor_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.InternalServerError,
    ],
)
def get_flavor(
    body: schemas.GetFlavorRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.FlavorResponse:
    """Get a flavor by ID.

    Args:
        body: get flavor request
        auth_data: authentication data

    Returns:
        flavor response
    """
    func_name = "get_flavor"
    logger.info(f"Call {func_name}: {body.flavor_id}")

    flavor_manager = scheduler.get_flavor_manager()
    if flavor_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Flavor manager not initialized")
        )
    # Visibility scoping: public flavors are visible to all users,
    # private flavors only to the owning project.
    # Super admins see all flavors.
    if _is_super_admin(auth_data):
        flavor = flavor_manager.get_flavor(str(body.flavor_id))
    else:
        flavor = flavor_manager.get_visible_flavor(
            str(body.flavor_id),
            project_id=_current_project_id(auth_data),
        )
    if flavor is None:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, f"Flavor not found: {body.flavor_id}"),
        )

    response = schemas.FlavorResponse.model_validate(flavor)
    response.device_groups = [
        uuid.UUID(dg_id)
        for dg_id in flavor_manager.get_flavor_device_groups(str(flavor.id))
    ]
    return response


@flavor_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.InternalServerError,
    ],
)
def get_flavors(
    body: schemas.GetFlavorsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> list[schemas.FlavorResponse]:
    """Get all flavors with optional filtering.

    Args:
        body: get flavors request with optional filter dict
        auth_data: authentication data

    Returns:
        list of flavor responses

    Filter example:
        {"flavor_name": "g1.all"} - filter by flavor_name
    """
    func_name = "get_flavors"
    logger.info(f"Call {func_name}: {body}")

    flavor_manager = scheduler.get_flavor_manager()
    if flavor_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Flavor manager not initialized")
        )
    # Visibility scoping: public flavors are visible to all users,
    # private flavors only to the owning project.
    # Super admins see all flavors.
    filter_conditions = None
    if body:
        filter_conditions = body.filters
    if _is_super_admin(auth_data):
        flavors = flavor_manager.get_flavor_responses(
            filters=filter_conditions
        )
    else:
        flavors = flavor_manager.get_flavor_responses(
            filters=filter_conditions,
            project_id=_current_project_id(auth_data),
        )
    return [schemas.FlavorResponse.model_validate(f) for f in flavors]


@flavor_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.InternalServerError,
    ],
)
def delete_flavors(
    body: schemas.DeleteFlavorsRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeleteFlavorsResponse:
    """Delete multiple flavors by IDs (batch).

    Iterates over each flavor_id, deletes it independently, and
    collects per-flavor results. Does not abort on individual
    failures.

    Args:
        body: delete flavors request (flavor_ids list)
        auth_data: authentication data

    Returns:
        delete flavors response with per-flavor results
    """
    func_name = "delete_flavors"
    logger.info(f"Call {func_name}: {body.flavor_ids}")

    flavor_manager = scheduler.get_flavor_manager()
    if flavor_manager is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Flavor manager not initialized")
        )
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )

    results_data = flavor_manager.delete_flavors(
        [str(fid) for fid in body.flavor_ids], db_filters=db_filters
    )

    results = []
    for flavor_id, success, error in results_data:
        results.append(
            schemas.DeleteFlavorResponseItem(
                flavor_id=flavor_id,
                success=success,
                error=error if not success else None,
            )
        )
    return schemas.DeleteFlavorsResponse(results=results)
