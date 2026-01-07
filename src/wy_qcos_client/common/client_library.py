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

import csv
import json
import logging
import requests
import uuid
from datetime import datetime

from schema import Schema

from .constant import HttpMethod

logger = logging.getLogger(__name__)


class ClientLibrary:
    """Client library."""

    @staticmethod
    def get_current_datetime():
        """Get current datetime.

        Returns:
            datetime
        """
        return datetime.now()

    @staticmethod
    def call_http_api(
        url,
        method,
        *,
        data=None,
        json=None,
        files=None,
        params=None,
        func_name=None,
        headers=None,
        auth=None,
        use_ssl=False,
        verify_ssl=True,
        cert_file=None,
        key_file=None,
        retries=1,
        timeout=30,
        success_http_code=[200, 201],
        debug=False,
    ):
        """Call http api.

        Args:
            url: api url
            method: http method
            data: data for http body (Default value = None)
            json: json data for http body (Default value = None)
            files: files for http body (Default value = None)
            params: params for http url (Default value = None)
            func_name: function name (Default value = None)
            headers: http headers (Default value = None)
            auth: http auth (Default value = None)
            use_ssl: if use ssl certificate
            verify_ssl: if verify ssl certificate (Default value = False)
            cert_file: ssl cert file
            key_file: ssl key file
            retries: times to retry if failed (Default value = 1)
            timeout: timeout in seconds (Default value = 10)
            success_http_code: success http status (Default value = [200)
            debug: enable or disable debug (Default value = False)
        """
        request_func = None
        r = None
        if debug:
            logger.info(
                f"Request [{func_name}]: {url}, "
                f"METHOD: {method.upper()}, HEADER: {headers}, "
                f"PARAMS: {params}, DATA: {data}, JSON: {json}"
            )
        if method == HttpMethod.POST:
            request_func = requests.post
        elif method == HttpMethod.PUT:
            request_func = requests.put
        elif method == HttpMethod.PATCH:
            request_func = requests.patch
        elif method == HttpMethod.DELETE:
            request_func = requests.delete
        else:
            request_func = requests.get

        cert = None
        if use_ssl and cert_file and key_file:
            cert = (cert_file, key_file)

        for i in range(1, retries + 1):
            r = request_func(
                url,
                headers=headers,
                params=params,
                data=data,
                files=files,
                json=json,
                auth=auth,
                verify=verify_ssl,
                timeout=timeout,
                cert=cert,
            )
            if r.status_code in success_http_code:
                break
        return r.status_code, r.reason, r.text, r

    @staticmethod
    def read_file(file_path, replace_pattern=None, customer_format=None):
        """Read text file.

        Args:
            file_path: file path
            replace_pattern: replace pattern (Default value = None)
            customer_format: customer format (Default value = None)

        Returns:
            file content
        """
        content = None
        with open(file_path, encoding="utf-8") as file:
            content = file.read()
        if replace_pattern:
            content = content.format(**replace_pattern)
        if customer_format:
            for k, v in customer_format.items():
                content = content.replace(k, v)
        return content

    @staticmethod
    def read_csv_file(file_path):
        content_list = []
        with open(file_path, encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                content_list.append([int(value) for value in row])
        return json.dumps(content_list)

    @staticmethod
    def validate_schema(
        value, schema_obj, allow_none=False, ignore_extra_keys=False
    ):
        """Validate schema values.

        Args:
            value: value to be validated
            schema_obj: schema obj
            allow_none: allow None value (Default value = False)
            ignore_extra_keys: ignore extra keys (Default value = False)

        Returns:
            success of failed (bool), error message list
        """
        success = True
        err_msg = None
        if value is None and allow_none:
            return True, None
        if not schema_obj:
            return False, ["schema is not defined, value is not allowed"]
        try:
            _schema = Schema(schema_obj, ignore_extra_keys=ignore_extra_keys)
            _schema.validate(value)
        except Exception as e:
            success = False
            err_msg = str(e)
        return success, [err_msg]

    @staticmethod
    def validate_values_enum(value, param_name, value_list, allow_none=False):
        """Validate values for enum.

        Args:
            value: value
            param_name: param name
            value_list: valid value list
            allow_none: allow None value (Default value = False)

        Returns:
            success of failed (bool), error message list
        """
        if value is None and allow_none:
            return True, None
        if value not in value_list:
            err_msg = (
                f"Invalid params: {param_name}={value}. "
                f"reason: valid values: {', '.join(value_list)}"
            )
            return False, [err_msg]
        return True, None

    @staticmethod
    def validate_values_uuid(value, param_name):
        """Validate values for uuid.

        Args:
            value: value
            param_name: param name

        Returns:
            success of failed (bool), error message list
        """
        try:
            uuid_obj = uuid.UUID(value, version=4)
            if str(uuid_obj) != value:
                err_msg = (
                    f"Invalid params: {param_name}={value}. "
                    f"reason: UUID version error"
                )
                return False, [err_msg]
        except ValueError:
            err_msg = (
                f"Invalid params: {param_name}={value}. "
                f"reason: UUID value error"
            )
            return False, [err_msg]
        return True, None

    @staticmethod
    def validate_values_range(
        value, param_name, min_value=None, max_value=None
    ):
        """Validate values for int range.

        Args:
            value: value
            param_name: param name
            min_value: minimum value (Default value = None)
            max_value: maximum value (Default value = None)

        Returns:
            success of failed (bool), error message list
        """
        err_msgs = []
        if min_value:
            if value < min_value:
                err_msgs.append(
                    f"Invalid params: {param_name}={value}. "
                    f"reason: value should >= {min_value}"
                )
        if max_value:
            if value > max_value:
                err_msgs.append(
                    f"Invalid params: {param_name}={value}. "
                    f"reason: value should <= {max_value}"
                )
        if err_msgs:
            return False, err_msgs
        return True, None

    @staticmethod
    def validate_values_length(
        value, param_name, min_value=None, max_value=None, allow_none=False
    ):
        """Validate values for int range.

        Args:
            value: value
            param_name: param name
            min_value: minimum value (Default value = None)
            max_value: maximum value (Default value = None)
            allow_none: allow None value (Default value = False)

        Returns:
            success of failed (bool), error message list
        """
        err_msgs = []
        if value is None and allow_none:
            return True, err_msgs
        if min_value:
            if len(value) < min_value:
                err_msgs.append(
                    f"Invalid params: {param_name}={value}. "
                    f"reason: length of value should >= {min_value}"
                )
        if max_value:
            if len(value) > max_value:
                err_msgs.append(
                    f"Invalid params: {param_name}={value}. "
                    f"reason: length of value should <= {max_value}"
                )
        if err_msgs:
            return False, err_msgs
        return True, None
