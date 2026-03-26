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

from uuid import UUID
import logging

from sqlalchemy.orm import Session

from wy_qcos.db.models import User
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.db.utils import db_utils
from wy_qcos.api.schemas.user import CreateUserRequest

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Database operation function library related to Users."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_user(self, user_create: CreateUserRequest):
        """Create a new user."""
        user_create_dict = user_create.model_dump()
        user_create_dict["hashed_password"] = db_utils.hash_password(
            user_create.password
        )
        del user_create_dict["password"]
        return self.create(User, **user_create_dict)

    def get_user_by_username(self, user_name: str):
        return self.get_by_attr(User, "username", user_name)

    def get_users(self):
        return self.get_all(User)

    def update_user(self, user_id: UUID, user_update: CreateUserRequest):
        """Update a user."""
        user_update_dict = user_update.model_dump()
        if user_update_dict.get("password"):
            user_update_dict["hashed_password"] = db_utils.hash_password(
                user_update.password
            )
            del user_update_dict["password"]
        return self.update(User, user_id, **user_update_dict)

    def delete_user_by_uuid(self, id: UUID):
        return self.delete_by_uuid(User, uuid=id)
