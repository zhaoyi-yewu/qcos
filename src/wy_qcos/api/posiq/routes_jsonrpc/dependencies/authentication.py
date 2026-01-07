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

import logging

from fastapi import Header

from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.common.config import Config
from wy_qcos.common.library import Library


logger = logging.getLogger(__name__)


def auth(
    x_qcos_virtual_instance_id: str | None = Header(
        None, alias="x-qcos-virtual-instance-id"
    ),
):
    success = True
    auth_data = None
    device_names = []
    instance_id = None

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
