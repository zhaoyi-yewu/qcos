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

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import job_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.scheduler.errors import FlavorNotFoundError
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
module_name = "FLAVOR"


@job_api_v1.method(
    tags=["flavor"],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.BadRequestError],
)
def create_flavor(
    body: schemas.CreateFlavorRequest,
) -> schemas.FlavorResponse:
    """Create a flavor (preset scheduling policy).

    Args:
        body: create flavor request

    Returns:
        flavor response
    """
    func_name = "create_flavor"
    logger.info(f"Call {func_name}: {body.name}")

    auto_scheduler = scheduler.get_auto_scheduler()
    if auto_scheduler is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Auto scheduler not initialized")
        )

    flavor_manager = auto_scheduler._flavor_manager

    # validate name
    if not body.name:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, "flavor name is required")
        )

    # check duplicate name
    existing = flavor_manager.get_flavors()
    for f in existing:
        if f.name == body.name:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, f"Flavor name already exists: {body.name}"),
            )

    flavor_data = {
        "name": body.name,
        "description": body.description,
        "is_public": body.is_public,
        "specs": body.specs,
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

    response = schemas.FlavorResponse.model_validate(flavor)
    return response


@job_api_v1.method(
    tags=["flavor"],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.BadRequestError],
)
def get_flavor(
    body: schemas.GetFlavorRequest,
) -> schemas.FlavorResponse:
    """Get a flavor by ID.

    Args:
        body: get flavor request

    Returns:
        flavor response
    """
    func_name = "get_flavor"
    logger.info(f"Call {func_name}: {body.flavor_id}")

    auto_scheduler = scheduler.get_auto_scheduler()
    if auto_scheduler is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Auto scheduler not initialized")
        )

    flavor_manager = auto_scheduler._flavor_manager
    flavor = flavor_manager.get_flavor(str(body.flavor_id))
    if flavor is None:
        raise FlavorNotFoundError(f"Flavor not found: {body.flavor_id}")

    response = schemas.FlavorResponse.model_validate(flavor)
    return response


@job_api_v1.method(
    tags=["flavor"],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.BadRequestError],
)
def get_flavors() -> list[schemas.FlavorResponse]:
    """Get all flavors.

    Returns:
        list of flavor responses
    """
    func_name = "get_flavors"
    logger.info(f"Call {func_name}")

    auto_scheduler = scheduler.get_auto_scheduler()
    if auto_scheduler is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Auto scheduler not initialized")
        )

    flavor_manager = auto_scheduler._flavor_manager
    flavors = flavor_manager.get_flavors()
    return [schemas.FlavorResponse.model_validate(f) for f in flavors]


@job_api_v1.method(
    tags=["flavor"],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.BadRequestError],
)
def delete_flavor(
    body: schemas.DeleteFlavorRequest,
) -> schemas.DeleteFlavorResponse:
    """Delete a flavor by ID.

    Args:
        body: delete flavor request

    Returns:
        delete flavor response
    """
    func_name = "delete_flavor"
    logger.info(f"Call {func_name}: {body.flavor_id}")

    auto_scheduler = scheduler.get_auto_scheduler()
    if auto_scheduler is None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, "Auto scheduler not initialized")
        )

    flavor_manager = auto_scheduler._flavor_manager
    success, error = flavor_manager.delete_flavor(str(body.flavor_id))
    if not success:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, f"Failed to delete flavor: {error}"),
        )

    return schemas.DeleteFlavorResponse(flavor_id=body.flavor_id)
