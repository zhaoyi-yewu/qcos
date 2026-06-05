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
import uuid as uuid_lib
from typing import Any

from sqlalchemy import select, delete, func
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
        self,
        model_class: type,
        uuid: str,
        child_attr_name: str | None = None,
        filters: dict | None = None,
    ):
        """Get a record from table by UUID string with optional filters.

        Args:
            model_class: The model class to query
            uuid: The UUID string or object
            child_attr_name: Optional child attribute name for eager loading
            filters: Optional dictionary with additional filter conditions
                    Example: {'project_id': 'xxx', 'user_id': 'yyy'}
                    Combines with id filter using AND logic

        Returns:
            Tuple[bool, Exception|None, record]: (success, error, record)
        """
        uuid_obj = uuid if isinstance(uuid, uuid_lib.UUID) else uuid

        # Prepare filters including id
        query_filters = filters.copy() if filters else {}
        query_filters["id"] = uuid_obj

        success, error, records = self.get_all(
            model_class,
            child_attr_name=child_attr_name,
            filters=query_filters,
        )

        if not success or records is None:
            return False, error, None

        # get_all returns list, but get_by_uuid should return single record
        if len(records) == 0:
            return True, None, None
        elif len(records) == 1:
            return True, None, records[0]
        else:
            return (
                False,
                Exception(f"The record with id {uuid_obj} is not unique."),
                None,
            )

    def get_all(
        self,
        model_class: type,
        child_attr_name: str | None = None,
        filters: dict | None = None,
    ):
        """Get all records with optional filtering.

        Args:
            model_class: The model class to query
            child_attr_name: Optional child attribute name for eager loading
            filters: Dictionary with filter conditions. Each key is a column
                    attribute name, value is the filter value. Example:
                    {'project_id': 'xxx', 'user_id': 'yyy', 'status': 'ACTIVE'}
                    Multiple filters are combined with AND logic

        Returns:
            Tuple[bool, Exception|None, list]: (success, error, records)
        """
        try:
            if child_attr_name is None:
                query = select(model_class)
            else:
                query = select(model_class).options(
                    selectinload(getattr(model_class, child_attr_name))
                )

            # Apply dynamic filters
            if filters:
                for key, value in filters.items():
                    if value is None:
                        continue

                    # Check if the attribute exists on the model
                    if hasattr(model_class, key):
                        # Handle list values with IN operator
                        if isinstance(value, list):
                            query = query.where(
                                getattr(model_class, key).in_(value)
                            )
                        else:
                            query = query.where(
                                getattr(model_class, key) == value
                            )
                    else:
                        logger.warning(
                            f"Filter key '{key}' does not exist on model "
                            f"{model_class.__name__}"
                        )

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
            logger.error(
                f"Error fetching records from {model_class.__name__} "
                f"with filters {filters}: {e}"
            )
            return False, e, None

    def count(self, model_class: type) -> int:
        """Get count of all records in table.

        Args:
            model_class: The model class to count

        Returns:
            Count of records, returns 0 on error
        """
        try:
            query = select(func.count()).select_from(model_class)
            result = self._db_session.execute(query)
            count = result.scalar()
            return count if count is not None else 0
        except Exception as e:
            logger.error(f"Error counting records in {model_class}: {e}")
            return 0

    def count_by_attr(
        self, model_class: type, attr_name: str, attr_value
    ) -> int:
        """Get count of records by attribute value.

        Args:
            model_class: The model class to count
            attr_name: The attribute name to filter by
            attr_value: The attribute value to match

        Returns:
            Count of matching records, returns 0 on error
        """
        try:
            query = (
                select(func.count())
                .select_from(model_class)
                .where(getattr(model_class, attr_name) == attr_value)
            )
            result = self._db_session.execute(query)
            count = result.scalar()
            return count if count is not None else 0
        except Exception as e:
            logger.error(
                f"Error counting records in {model_class} "
                f"by {attr_name}={attr_value}: {e}"
            )
            return 0

    def count_with_filters(
        self, model_class: type, filters: dict | None = None
    ) -> int:
        """Get count of records with optional filtering.

        Args:
            model_class: The model class to count
            filters: Dictionary with filter conditions. Each key is a column
                attribute name, value is the filter value. Multiple filters
                are combined with AND logic. Example::

                    {
                        "project_id": "xxx",
                        "user_id": "yyy",
                        "job_status": "COMPLETED",
                    }

        Returns:
            Count of matching records, returns 0 on error
        """
        try:
            query = select(func.count()).select_from(model_class)

            # Apply dynamic filters
            if filters:
                for key, value in filters.items():
                    if value is None:
                        continue
                    if hasattr(model_class, key):
                        # Handle list values with IN operator
                        if isinstance(value, list):
                            query = query.where(
                                getattr(model_class, key).in_(value)
                            )
                        else:
                            query = query.where(
                                getattr(model_class, key) == value
                            )
                    else:
                        logger.warning(
                            f"Filter key '{key}' does not exist on model "
                            f"{model_class.__name__}"
                        )

            result = self._db_session.execute(query)
            count = result.scalar()
            return count if count is not None else 0
        except Exception as e:
            logger.error(
                f"Error counting records in {model_class} "
                f"with filters {filters}: {e}"
            )
            return 0

    def update(self, model_class: type, uuid: str, **kwargs: Any):
        """Update a record with UUID string using args."""
        try:
            success, error, db_record = self.get_by_uuid(model_class, uuid)
            if not success:
                # If get_by_uuid failed with actual error, propagate the error
                return False, error, None
            if db_record:
                id_attr_name = "id"
                if id_attr_name in kwargs:
                    kwargs.pop(id_attr_name)
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
            # Accept uuid.UUID or string and let SQLAlchemy type handle binding
            uuid_obj = uuid if isinstance(uuid, uuid_lib.UUID) else uuid

            query = delete(model_class).where(
                getattr(model_class, id_attr_name) == uuid_obj
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

    def flush(self) -> None:
        """Flush pending changes to database without committing."""
        self._db_session.flush()

    def refresh(self, obj) -> None:
        """Refresh an ORM object to get latest committed data."""
        self._db_session.refresh(obj)
