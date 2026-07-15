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

from datetime import datetime
import logging

from fastapi import Depends, Request

from wy_qcos.api.schemas import project as schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import project_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from .dependencies.authentication import auth


logger = logging.getLogger(__name__)
module_name = "PROJECT"


def get_project_manager(request: Request):
    """Get project manager.

    Args:
        request: request object

    Returns:
        project manager object
    """
    return request.app.state._project_manager


@project_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.ConflictError, jsonrpc_errors.BadRequestError],
)
def create_project(
    body: schemas.CreateProjectRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.CreateProjectResponse:
    """Create a new project.

    Args:
        body: project creation request
        request: request object
        auth_data: auth data

    Returns:
        Create project response
    """
    func_name = "create_project"
    logger.info(f"Call {func_name}: project_name={body.project_name}")

    project_name = body.project_name
    description = body.description

    # validate project_name
    success, err_msg = Library.validate_name(project_name)
    if not success:
        jsonrpc_errors.handle_error_bad_requests(
            "PROJECT",
            "create_project",
            (False, err_msg),
        )

    # Get project manager from request state
    project_manager = get_project_manager(request)

    # Create project using ProjectManager
    try:
        project = project_manager.create_project(
            project_name=project_name,
            description=description,
        )
        _response_info = _get_project_response(project)
        response_info = schemas.CreateProjectResponse.model_validate(
            _response_info
        )
    except ValueError as e:
        error_msg = str(e)
        # Handle different error types based on error message
        if "already exists" in error_msg:
            jsonrpc_errors.handle_error_conflict(
                module_name,
                func_name,
                (False, error_msg),
            )
        else:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, error_msg),
            )
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )
    return response_info


@project_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_project(
    body: schemas.GetProjectRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetProjectResponse:
    """Get project information by ID.

    Args:
        body: get project request (contains project_id)
        request: request object
        auth_data: auth data

    Returns:
        Get project response
    """
    func_name = "get_project"
    logger.info(f"Call {func_name}: project_id={body.project_id}")

    project_id = str(body.project_id)

    # Get project manager from request state
    project_manager = get_project_manager(request)

    # Get project using ProjectManager
    try:
        project = project_manager.get_project_by_id(project_id)
        if not project:
            jsonrpc_errors.handle_error_not_found(
                module_name,
                func_name,
                (False, f"Project with ID '{project_id}' not found"),
            )
        _response_info = _get_project_response(project)
        response_info = schemas.GetProjectResponse.model_validate(
            _response_info
        )
    except ValueError as e:
        # ProjectManager validation errors
        error_msg = str(e)
        logger.warning(f"Error getting project {project_id}: {error_msg}")
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, error_msg)
        )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(
            f"Unexpected error getting project {project_id}: {str(e)}"
        )
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@project_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]}, errors=[]
)
def get_projects(
    request: Request,
    body: schemas.GetProjectsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.GetProjectsResponse]:
    """Get projects with optional filtering.

    Args:
        request: request object
        body: get projects request with optional filter dict
        auth_data: auth data

    Returns:
        Dictionary of projects keyed by project ID

    Filter example:
        {"name": "default"} - filter by project name
    """
    func_name = "get_projects"
    logger.info(f"Call {func_name}: {body}")

    # Get project manager from request state
    project_manager = get_project_manager(request)

    # Extract filter conditions from request body
    filter_conditions = None
    if body:
        filter_conditions = body.filters

    # Get projects using ProjectManager with optional filtering
    try:
        projects_dict = project_manager.get_projects(filters=filter_conditions)
        projects = list(projects_dict.values()) if projects_dict else []
        # Build response
        response_info = {}
        for project in projects:
            project_data = _get_project_response(project)
            response_info[str(project.id)] = (
                schemas.GetProjectsResponse.model_validate(project_data)
            )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error getting projects: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@project_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.ConflictError,
    ],
)
def update_project(
    body: schemas.UpdateProjectRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.UpdateProjectResponse:
    """Update project information by ID.

    Args:
        body: project update request (contains project_id)
        request: request object
        auth_data: auth data

    Returns:
        Update project response
    """
    func_name = "update_project"
    logger.info(f"Call {func_name}: project_id={body.project_id}")

    project_id = str(body.project_id)
    project_name = body.project_name
    description = body.description

    # validate project_name if provided
    if project_name:
        success, err_msg = Library.validate_name(project_name)
        if not success:
            jsonrpc_errors.handle_error_bad_requests(
                "PROJECT",
                "update_project",
                (False, err_msg),
            )

    # Get project manager from request state
    project_manager = get_project_manager(request)

    # Update project using ProjectManager
    try:
        project = project_manager.update_project(
            project_id=project_id,
            project_name=project_name,
            description=description,
        )
        _response_info = _get_project_response(project)
        response_info = schemas.UpdateProjectResponse.model_validate(
            _response_info
        )
    except ValueError as e:
        error_msg = str(e)
        # Handle different error types based on error message
        if "already exists" in error_msg:
            jsonrpc_errors.handle_error_conflict(
                module_name, func_name, (False, error_msg)
            )
        elif "not found" in error_msg.lower():
            jsonrpc_errors.handle_error_not_found(
                module_name, func_name, (False, error_msg)
            )
        else:
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, error_msg)
            )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Error updating project {project_id}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@project_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.ConflictError,
    ],
)
def delete_project(
    body: schemas.DeleteProjectRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeleteProjectResponse:
    """Delete project by ID.

    Args:
        body: delete project request (contains project_id)
        request: request object
        auth_data: auth data

    Returns:
        Delete project response
    """
    func_name = "delete_project"
    logger.info(f"Call {func_name}: project_id={body.project_id}")

    project_id = str(body.project_id)

    # Get project manager from request state
    project_manager = get_project_manager(request)

    # Delete project using ProjectManager
    try:
        project = project_manager.delete_project(project_id=project_id)
        _response_info = {
            "id": project_id,
            "name": project.name,
            "deleted_at": datetime.now().isoformat(),
        }
        response_info = schemas.DeleteProjectResponse.model_validate(
            _response_info
        )
    except ValueError as e:
        error_msg = str(e)
        # Handle different error types based on error message
        if (
            "reserved" in error_msg.lower()
            or "cannot delete" in error_msg.lower()
        ):
            jsonrpc_errors.handle_error_conflict(
                module_name, func_name, (False, error_msg)
            )
        elif "not found" in error_msg.lower():
            jsonrpc_errors.handle_error_not_found(
                module_name, func_name, (False, error_msg)
            )
        else:
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, error_msg)
            )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


def _get_project_response(project) -> dict:
    """Build project response dict from ORM model.

    Args:
        project: Project ORM model instance

    Returns:
        dict with project response fields
    """
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "created_at": (
            project.created_at.isoformat()
            if hasattr(project.created_at, "isoformat")
            else str(project.created_at)
        ),
        "updated_at": (
            project.updated_at.isoformat()
            if hasattr(project.updated_at, "isoformat")
            else str(project.updated_at)
        ),
    }
