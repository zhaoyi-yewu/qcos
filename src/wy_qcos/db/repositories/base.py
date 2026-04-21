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

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ControllerDatabaseError(Exception):
    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def __repr__(self):
        return self._message

    def __str__(self):
        return self._message


class BaseRepository:
    def __init__(self, db_session: Session) -> None:
        self._db_session = db_session

    def create(self, model_class: type, **kwargs: Any):
        """Create a record in table."""
        try:
            db_record = model_class(**kwargs)
            self._db_session.add(db_record)
            self._db_session.commit()
            self._db_session.refresh(db_record)
            return True, None, db_record
        except Exception as e:
            return False, e, None

    def get_by_attr(
        self,
        model_class: type,
        attr_name: str,
        attr_value,
        child_attr_name: str | None = None,
        unique: bool | None = True,
    ):
        """Get a record from table by attribute."""
        if child_attr_name is None:
            query = select(model_class).where(
                getattr(model_class, attr_name) == attr_value
            )
        else:
            query = (
                select(model_class)
                .options(selectinload(getattr(model_class, child_attr_name)))
                .where(getattr(model_class, attr_name) == attr_value)
            )

        result = self._db_session.execute(query)
        db_records = result.scalars().all()
        if unique:
            if len(db_records) == 0:
                return False, None, None
            elif len(db_records) == 1:
                # Always refresh the ORM object to avoid stale cache
                try:
                    self._db_session.refresh(db_records[0])
                except Exception as e:
                    logger.debug(f"Refresh error for read-only: {e}")
                return True, None, db_records[0]
            else:
                return (
                    False,
                    Exception(
                        f"The record which {attr_name} is {attr_value} in "
                        f"table{model_class} is not unique."
                    ),
                    None,
                )
        else:
            # Refresh all objects in the result list
            for obj in db_records:
                try:
                    self._db_session.refresh(obj)
                except Exception as e:
                    logger.debug(f"Refresh error for record: {e}")
            return True, None, db_records

    def get_by_uuid(
        self, model_class: type, uuid: str, child_attr_name: str | None = None
    ):
        """Get a record from table by UUID string."""
        id_attr_name = "id"
        if not child_attr_name:
            query = select(model_class).where(
                getattr(model_class, id_attr_name) == uuid
            )
        else:
            query = (
                select(model_class)
                .options(selectinload(getattr(model_class, child_attr_name)))
                .where(getattr(model_class, id_attr_name) == uuid)
            )
        try:
            result = self._db_session.execute(query)
            db_record = result.scalars().first()
            if db_record:
                try:
                    self._db_session.refresh(db_record)
                except Exception as e:
                    logger.debug(f"Refresh error for record: {e}")
            return True, None, db_record
        except Exception as e:
            return False, e, None

    def get_all(self, model_class: type, child_attr_name: str | None = None):
        """Get all records."""
        if child_attr_name is None:
            query = select(model_class)
        else:
            query = select(model_class).options(
                selectinload(getattr(model_class, child_attr_name))
            )
        try:
            result = self._db_session.execute(query)
            db_records = result.scalars().all()
            # Refresh all objects in the result list
            for obj in db_records:
                try:
                    self._db_session.refresh(obj)
                except Exception as e:
                    logger.debug(f"Refresh error for record: {e}")
            return True, None, db_records
        except Exception as e:
            return False, e, None

    def update(self, model_class: type, uuid: str, **kwargs: Any):
        """Update a record with UUID string using args."""
        try:
            success, error, db_record = self.get_by_uuid(model_class, uuid)
            if not success:
                # If get_by_uuid failed, propagate the error
                return False, error, None
            id_attr_name = "id"
            if id_attr_name in kwargs:
                kwargs.pop(id_attr_name)
            if db_record:
                for key, value in kwargs.items():
                    # Allow setting fields to None (for clearing fields)
                    if hasattr(model_class, key):
                        setattr(db_record, key, value)
                self._db_session.commit()
                # Refresh to ensure we have the latest committed data
                self._db_session.refresh(db_record)
            return True, None, db_record
        except Exception as e:
            self.rollback()
            return False, e, None

    def delete_by_uuid(self, model_class: type, uuid: str):
        """Delete a record from table by UUID string."""
        try:
            id_attr_name = "id"
            query = delete(model_class).where(
                getattr(model_class, id_attr_name) == uuid
            )
            result = self._db_session.execute(query)
            self._db_session.commit()
            return result.rowcount > 0, None
        except Exception as e:
            return False, e

    def delete_by_attr(self, model_class: type, attr_name: str, attr_value):
        """Delete a record from table by attribute."""
        try:
            query = delete(model_class).where(
                getattr(model_class, attr_name) == attr_value
            )
            result = self._db_session.execute(query)
            self._db_session.commit()

            return result.rowcount > 0, None
        except Exception as e:
            return False, e

    def rollback(self) -> None:
        self._db_session.rollback()

    def commit(self) -> None:
        self._db_session.commit()
