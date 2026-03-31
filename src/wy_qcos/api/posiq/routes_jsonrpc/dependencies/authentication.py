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

from fastapi import Depends, Header, Request

from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s, Library
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    JWTStrategy,
    AuthenticationBackend,
    CookieTransport,
)
from wy_qcos.db.models.user import User as UserModel

logger = logging.getLogger(__name__)


def auth(
    x_qcos_virtual_instance_id: str | None = Header(
        None, alias="x-qcos-virtual-instance-id"
    ),
):
    """Authentication dependency for virtual instance access.

    Args:
        x_qcos_virtual_instance_id: Virtual instance ID header

    Returns:
        Authentication data or None for admin users
    """
    success = True
    auth_data: dict[str, list[str] | str | None] | None = None
    device_names = []
    instance_id = None

    # TODO(zhaoyi)
    if Config.ENABLE_USER_MGMT:
        auth_data = {
            "roles": [Constant.ROLE_ADMIN]  # TODO
        }
        return auth_data

    if not Config.ENABLE_VIRT:
        return None

    if x_qcos_virtual_instance_id is None:
        success = False

    if success:
        success, err_msg, device_names, instance_id = (
            Library.decrypt_virtual_instance_id(
                x_qcos_virtual_instance_id,
                salt=Config.PASSWORD_SALT,
                encode=True,
            )
        )

    if not success:
        jsonrpc_errors.handle_error_unauthorized(
            "authentication",
            "auth",
            (False, ["Unauthorized access to the instance"]),
        )

    if "all" in device_names and instance_id == "all":  # admin user
        auth_data = None
    else:
        auth_data = {
            "device_names": device_names,
            "instance_id": instance_id,
        }
    return auth_data


class RoleChecker:
    def __call__(self, request: Request, auth_data: dict = Depends(auth)):
        # Check user management is enabled
        if not Config.ENABLE_USER_MGMT:
            return True

        # Reject access if no authentication data
        if not auth_data:
            jsonrpc_errors.handle_error_unauthorized(
                "authentication",
                "require_permission",
                (False, ["Authentication required"]),
            )

        # Get user roles
        user_roles = auth_data.get("roles", [])
        if not user_roles:
            jsonrpc_errors.handle_error_forbidden(
                "authentication",
                "require_permission",
                (False, ["No roles assigned to user"]),
            )

        # Check permissions
        obj = request.url.path
        act = "call"
        has_permission = False
        for role in user_roles:
            if request.app.state._user_manager.perms_check_enforce(
                role, obj, act
            ):
                has_permission = True
                break

        if not has_permission:
            jsonrpc_errors.handle_error_forbidden(
                "authentication",
                "require_permission",
                (False, [f"Insufficient permissions for {obj}:{act}"]),
            )
        return True


# JWT Authentication Configuration
# todo(zhaoyi)
SECRET = _s("abc")
LIFETIME_SECONDS = 3600 * 24 * 7  # 7 days


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=LIFETIME_SECONDS)


# Cookie transport for JWT
cookie_transport = CookieTransport(
    cookie_name="qcos_auth",
    cookie_secure=True,  # Set to False in development
    cookie_httponly=True,
    cookie_samesite="lax",
)

# Authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


# User manager dependency (to be implemented)
async def get_user_manager():
    """Get user manager instance."""
    # This will be implemented when we have the actual user manager
    pass


# FastAPI-Users instance
fastapi_users = FastAPIUsers[UserModel, int](
    get_user_manager,
    [auth_backend],
)

# FastAPI-Users dependencies
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
