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

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from .base import BaseFilter

logger = logging.getLogger(__name__)


class InputConstraintsFilter(BaseFilter):
    """Filter devices by driver input constraints.

    Validates three aspects of a job request against the driver's
    declared capabilities:

    1. **job_shots**: checks the job's ``shots`` against the driver's
       ``input_constrains["job_shots"]`` schema (a schema library
       ``Schema`` object or ``None``) via ``Library.validate_schema``.

       * When the driver declares no ``job_shots`` constraint (``None``),
         the device passes.
       * When the job's ``shots`` is ``None``, the device passes.
       * Otherwise validate ``shots`` against the schema; devices whose
         schema rejects the shots value are filtered out.

    2. **circuit_aggregation**: checks the job's ``circuit_aggregation``
       against the driver's ``enable_circuit_aggregation`` flag.

       * When ``enable_circuit_aggregation`` is ``True``, any
         ``circuit_aggregation`` value passes.
       * When ``enable_circuit_aggregation`` is ``False``, only
         ``circuit_aggregation`` of ``None`` or
         ``Constant.AGGREGATION_TYPE_NONE`` ("None") passes.

    3. **driver_options**: checks the job's ``driver_options`` against
       the driver's ``driver_options_schema`` via
       ``Library.validate_schema``.

       * When ``driver_options`` is ``None``, the device passes.
       * When the driver declares no ``driver_options_schema``, the
         device passes.
       * Otherwise validate ``driver_options`` against the schema;
         devices whose schema rejects the value are filtered out.

    4. **transpiler_options**: checks the job's ``transpiler_options``
       against the driver's ``transpiler_options_schema`` via
       ``Library.validate_schema``.

       * When ``transpiler_options`` is ``None``, the device passes.
       * When the driver declares no ``transpiler_options_schema``
         (empty or None), the device passes.
       * Otherwise validate ``transpiler_options`` against the schema;
         devices whose schema rejects the value are filtered out.
    """

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        # 1. job_shots constraint
        if not self._check_job_shots(obj, spec):
            return False
        # 2. circuit_aggregation constraint
        if not self._check_circuit_aggregation(obj, spec):
            return False
        # 3. driver_options constraint
        if not self._check_driver_options(obj, spec):
            return False
        # 4. transpiler_options constraint
        if not self._check_transpiler_options(obj, spec):
            return False
        return True

    @staticmethod
    def _check_job_shots(obj: DeviceState, spec: RequestSpec) -> bool:
        """Check job_shots against the driver's constraint schema."""
        shots = spec.shots
        # shots is None: nothing to validate, pass
        if shots is None:
            return True
        schema = obj.input_constrains.get("job_shots")
        # driver declares no constraint for job_shots, pass
        if schema is None:
            return True
        success, _ = Library.validate_schema(shots, schema)
        logger.debug(
            f"InputConstraintsFilter: device_name: {obj.name}. "
            f"shots: {shots}, schema: {schema}, success: {success}"
        )
        return success

    @staticmethod
    def _check_circuit_aggregation(
        obj: DeviceState, spec: RequestSpec
    ) -> bool:
        """Check circuit_aggregation against driver capability."""
        ca = spec.circuit_aggregation
        # driver supports aggregation: any value passes
        if obj.enable_circuit_aggregation:
            return True
        # driver does not support aggregation: only None or "None" pass
        if ca is None or ca == Constant.AGGREGATION_TYPE_NONE:
            return True
        logger.debug(
            f"InputConstraintsFilter: device_name: {obj.name}. "
            f"circuit_aggregation: {ca}, "
            f"enable_circuit_aggregation: False, filtered out"
        )
        return False

    @staticmethod
    def _check_driver_options(obj: DeviceState, spec: RequestSpec) -> bool:
        """Check driver_options against the driver's options schema."""
        options = spec.driver_options
        # driver_options is None: nothing to validate, pass
        if options is None:
            return True
        schema = obj.driver_options_schema
        # driver declares no options schema, pass
        if not schema:
            return True
        success, _ = Library.validate_schema(options, schema)
        logger.debug(
            f"InputConstraintsFilter: device_name: {obj.name}. "
            f"driver_options: {options}, schema: {schema}, success: {success}"
        )
        return success

    @staticmethod
    def _check_transpiler_options(obj: DeviceState, spec: RequestSpec) -> bool:
        """Check transpiler_options against the driver's schema."""
        options = spec.transpiler_options
        # transpiler_options is None: nothing to validate, pass
        if options is None:
            return True
        schema_dict = obj.transpiler_options_schema
        # driver declares no transpiler_options schema, pass
        if not schema_dict:
            return True
        schema = Library.convert_schema(schema_dict)
        # driver declares no transpiler_options schema, pass
        if not schema:
            return True
        success, _ = Library.validate_schema(options, schema)
        logger.debug(
            f"InputConstraintsFilter: device_name: {obj.name}. "
            f"transpiler_options: {options}, schema: {schema}, "
            f"success: {success}"
        )
        return success
