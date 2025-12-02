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

import aiohttp
import asyncio
import base64
import copy
import csv
import fnmatch
import hashlib
import importlib
import inspect
import json
import logging
import math
import numpy as np
import os
import pkgutil
import random
import re
import requests
import signal
import tempfile
import time
import tomlkit
import uuid
import zipfile

from aiohttp import ClientTimeout, ClientError
from cryptography.fernet import Fernet
from datetime import datetime
from http import HTTPStatus
from schema import Schema
from urllib.parse import urlparse

from .constant import HttpCode, HttpHeaders, HttpMethod, Constant

logger = logging.getLogger(__name__)


class Library:
    """Library."""

    @staticmethod
    def get_brief_description(description):
        output_list = []
        tokens = description.split("\n")
        for token in tokens:
            _token = token.strip()
            if _token:
                output_list.append(_token)
        return ". ".join(output_list)

    @staticmethod
    def update_dict(dictionary, new_kvs):
        """Update a dictionary.

        Args:
            dictionary: dictionary to be updated
            new_kvs: new key/values

        Returns:
            updated dictionary
        """
        for key, value in new_kvs.items():
            if key in dictionary:
                dictionary[key] = value
        return dictionary

    @staticmethod
    def remove_duplicates(lst):
        """Remove duplicates elements from a list.

        Args:
            lst: list

        Returns:
            list
        """
        new_list = []
        for element in lst:
            if element not in new_list:
                new_list.append(element)
        return new_list

    @staticmethod
    def kill_pid(pid_file):
        """Kill existing process from pid file.

        Args:
            pid_file: pid file path
        """
        pid = None
        if not os.path.exists(pid_file):
            return
        try:
            # Read and validate PID file content
            with open(pid_file, encoding="utf-8") as f:
                pid_str = f.read().strip()
                if not pid_str.isdigit():
                    raise ValueError(f"Invalid pid format: {pid_str}")
                pid = int(pid_str)
            # Attempt to terminate the process by sending SIGTERM signal
            os.kill(pid, signal.SIGTERM)
            # Wait for process to exit
            time.sleep(1)
        except ValueError as e:
            print(f"Failed to process PID file: {e}")
        except ProcessLookupError:
            print(f"Process: {pid} does not exist")
        except PermissionError:
            print(f"Insufficient permissions to terminate process: {pid}")
        except Exception as e:
            print(f"Error occurred while terminating process: {e}")
        finally:
            # Delete pid file
            try:
                os.remove(pid_file)
            except OSError as e:
                print(f"Failed to delete PID file: {e}")

    @staticmethod
    def create_file(file_path, file_content, mkdir=False, mode=None):
        """Create file.

        Args:
            file_path: file path
            file_content: file content
            mkdir: if make dir
            mode: file mode

        Returns:
            success, error messages
        """
        if mkdir:
            _dir = os.path.dirname(file_path)
            Library.mkdirs(_dir)
        with open(file_path, "wb") as output:
            output.write(file_content.encode("utf-8"))
        if mode:
            try:
                os.chmod(file_path, mode)
            except Exception as e:
                return False, f"failed to write file: {file_path}. {e}"
        return True, None

    @staticmethod
    def create_pid_file(file_path):
        """Crete pid file.

        Args:
            file_path: file path
        """
        pid = os.getpid()
        Library.create_file(file_path, str(pid))

    @staticmethod
    def create_temp_file(file_content, dir=None, dir_mode=None):
        """Create temp file.

        Args:
            file_content: file content
            dir: directory to create temp file
            dir_mode: directory mode

        Returns:
            temp_dir_prefix
        """
        # pylint: disable=consider-using-with
        Library.mkdirs(dir, mode=dir_mode)
        tf = tempfile.NamedTemporaryFile(delete=True, mode="w+b", dir=dir)
        try:
            if isinstance(file_content, str):
                tf.write(file_content.encode("utf-8"))
            elif isinstance(file_content, bytes):
                tf.write(file_content)
            else:
                raise TypeError("file_content type must be str or bytes")
            tf.seek(0)
        except Exception as e:
            tf.close()
            raise e
        return tf

    @staticmethod
    def rm_file(file_path):
        """Remove file.

        Args:
            file_path: file path

        Returns:
            True or False
        """
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                return False, f"failed to remove file: {file_path}. {e}"
        return True, None

    @staticmethod
    def find_dirs(base_dir="/", pattern="*", recursive=False, excludes=[]):
        """Find all dirs.

        Args:
            base_dir: base dir to search (Default value = "/")
            pattern: match pattern (Default value = "*")
            recursive: recursive search (Default value = False)
            excludes: excluded patterns (Default value = [])

        Returns:
            matched dir list
        """
        dirs = []
        if os.path.isdir(base_dir):
            dirs.append(base_dir)
            if recursive:
                for root, dir_names, filenames in os.walk(base_dir):
                    matched_dirs = set(fnmatch.filter(dir_names, pattern))
                    excluded_dirs = set()
                    for exclude in excludes:
                        _excluded_dirs = set(
                            fnmatch.filter(matched_dirs, exclude)
                        )
                        excluded_dirs.update(_excluded_dirs)
                    included_dirs = matched_dirs - excluded_dirs
                    for dir_name in included_dirs:
                        _dir_name = os.path.join(root, dir_name)
                        if _dir_name not in dirs:
                            dirs.append(_dir_name)
        return dirs

    @staticmethod
    def find_files(base_dir, pattern="*", recursive=False, exclusives=None):
        """Find files under given dir.

        Args:
            base_dir: base dir to search
            pattern: match pattern (Default value = "*")
            recursive: recursive search (Default value = False)
            exclusives: filename to exclude (Default value = None)

        Returns:
            file list
        """
        files = []
        if recursive:
            for root, dirnames, filenames in os.walk(base_dir):
                for filename in fnmatch.filter(filenames, pattern):
                    file_path = os.path.join(root, filename)
                    skip = False
                    if exclusives:
                        for exc in exclusives:
                            if exc in file_path:
                                skip = True
                                continue
                    if not skip:
                        files.append(file_path)
        else:
            if not os.path.isdir(base_dir):
                return files
            list_of_files = os.listdir(base_dir)
            for entry in list_of_files:
                if fnmatch.fnmatch(entry, pattern):
                    files.append(os.path.join(base_dir, entry))
        return files

    @staticmethod
    def mkdir(dir_name, mode=None):
        """Create dir.

        Args:
            dir_name: dir name
            mode: dir mode

        Returns:
            True or False
        """
        if not os.path.exists(dir_name):
            if mode:
                os.mkdir(dir_name, mode)
            else:
                os.mkdir(dir_name)
            return True
        return False

    @staticmethod
    def mkdirs(dir, mode=None):
        """Create dirs.

        Args:
            dir: dir name
            mode: dir mode
        """
        sub_path = os.path.dirname(dir)
        if not os.path.exists(sub_path):
            Library.mkdirs(sub_path, mode)
        if not os.path.exists(dir):
            if mode:
                os.mkdir(dir, mode=mode)
            else:
                os.mkdir(dir)

    @staticmethod
    def rmdir(dir):
        """Remove dir.

        Args:
            dir: dir name

        Returns:
            success, error messages
        """
        try:
            os.rmdir(dir)
        except Exception as e:
            return False, f"failed to remove dir: {dir}. {e}"
        return True, None

    @staticmethod
    def import_classes(
        pkg_dir,
        base_module_name="drivers",
        base_dir=None,
        base_class=None,
        excluded_class=None,
    ):
        """Import class from package dir.

        Args:
            pkg_dir: package dir
            base_module_name: base module name (Default value = "drivers")
            base_dir: base dir (Default value = None)
            base_class: base class (Default value = None)
            excluded_class: excluded class (Default value = None)

        Returns:
            class dict
        """
        classes = {}
        for module_loader, name, is_pkg in pkgutil.iter_modules([pkg_dir]):
            module_path = module_loader.path.replace(base_dir, "")
            module_name = (
                f"{base_module_name}{module_path.replace('/', '.')}.{name}"
            )
            try:
                module = importlib.import_module(module_name)
                for _, obj in inspect.getmembers(module):
                    if inspect.isclass(obj):
                        if issubclass(obj, base_class):
                            cls_name = obj.__name__
                            if excluded_class and Library.str_match(
                                cls_name, excluded_class
                            ):
                                continue
                            classes[cls_name] = obj
            except Exception as e:
                logger.error(
                    f"Failed to import module: {module_name}. Reason: {e}"
                )
        return classes

    @staticmethod
    def str_match(str, regex, ignore_case=False):
        """Match string with regex.

        Args:
            str: string
            regex: regex pattern
            ignore_case: ignore case (Default value = False)

        Returns:
            bool
        """
        if ignore_case:
            reg = re.compile(regex, re.IGNORECASE)
        else:
            reg = re.compile(regex)
        if reg.findall(str):
            return True
        return False

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
    def read_toml_file(file_path: str):
        """Read toml file.

        Args:
            file_path: toml file path
            file_path: str:

        Returns:
            success, err_msg, toml dict
        """
        try:
            with open(file_path, "rb") as _file:
                return True, None, tomlkit.load(_file)
        except FileNotFoundError:
            return False, f"file: {file_path} does not exist", None
        except Exception as e:
            return False, f"toml parser exception: {e}", None

    @staticmethod
    def create_toml(file_path: str, data: dict):
        """Write dict to toml file.

        Args:
            file_path: file_path
            data: data to write

        Returns:
            success, err_msg
        """
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                tomlkit.dump(data, file)
            return True, None
        except Exception as e:
            return False, f"failed to write toml file: {file_path}. {e}"

    @staticmethod
    def get_current_datetime():
        """Get current datetime.

        Returns:
            datetime
        """
        return datetime.now()

    @staticmethod
    def create_uuid(prefix=[]):
        random_bytes = bytearray(random.getrandbits(8) for _ in range(16))
        random_bytes[6] = (random_bytes[6] & 0x0F) | 0x40
        random_bytes[8] = (random_bytes[8] & 0x3F) | 0x80
        if prefix:
            i = 0
            for _prefix in prefix:
                random_bytes[i] = _prefix
                i += 1
        new_uuid = uuid.UUID(bytes=bytes(random_bytes))
        return new_uuid

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

    @staticmethod
    def validate_values_list(value, param_name, value_type, allow_none=False):
        """Validate values for list.

        Args:
            value: value
            param_name: param name
            value_type: data type of value
            allow_none: allow None value (Default value = False)

        Returns:
            success of failed (bool), error message list
        """
        if not isinstance(value, list):
            err_msg = (
                f"Invalid params: {param_name}={value}. "
                f"reason: type: list is required"
            )
            return False, [err_msg]
        for _value in value:
            if not isinstance(_value, value_type):
                err_msg = (
                    f"Invalid params: {param_name}={value}. "
                    f"reason: valid list element value type: "
                    f"{value_type}"
                )
                return False, [err_msg]
            if not allow_none and not _value:
                err_msg = (
                    f"Invalid params: {param_name}={value}. "
                    f"reason: None or empty element in list is "
                    f"not allowed"
                )
                return False, [err_msg]
        return True, None

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
    def validate_qubo_matrices(qubo_matrices):
        """Validate qubo matrices.

        Args:
            qubo_matrices: qubo matrices

        Returns:
            success of failed (bool), error message
        """
        if not qubo_matrices:
            return False, "qubo matrices list cannot be an empty list"
        try:
            matrices = np.array(qubo_matrices, dtype=float)
        except Exception as e:
            return False, f"Abnormal qubo matrices list, error: {str(e)}"
        matrices_shape = matrices.shape
        if len(matrices_shape) != 3:
            return False, "Current input qubo matrices list is not 3D list"
        for i in range(matrices_shape[0]):
            try:
                matrix = np.array(qubo_matrices[i], dtype=float)
            except Exception as e:
                return False, (
                    f"matrix in the list is "
                    f"a non-regular matrix, error: {str(e)}"
                )
            matrix_shape = matrix.shape
            if matrix_shape[0] != matrix_shape[1]:
                return False, f"The {i + 1}-th matrix is not square matrix"
            elif matrix_shape[0] > Constant.MAX_QUBO_QUBITS:
                return False, (
                    f"The {i + 1}-th Matrix has {matrix_shape[0]} "
                    f"qubits, exceeding the maximum limit of "
                    f"{Constant.MAX_QUBO_QUBITS}"
                )
        return True, None

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
        verify_ssl=False,
        retries=1,
        timeout=10,
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
            verify_ssl: if verify ssl certificate (Default value = False)
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
            )
            if r.status_code in success_http_code:
                break
        return r.status_code, r.reason, r.text, r

    @staticmethod
    async def async_call_http_api(
        url,
        method,
        *,
        data=None,
        json=None,
        params=None,
        func_name=None,
        headers=None,
        auth=None,
        retries=1,
        timeout=10,
        success_http_code=[200, 201],
        debug=False,
    ):
        """Async call http api.

        Args:
            url: api url
            method: http method
            data: data for http body
            json: json data for http body
            params: params for http url
            func_name: function name
            headers: http headers
            auth: http auth
            retries: times to retry if failed
            timeout: timeout in seconds
            success_http_code: success http status
            debug: enable or disable debug
        """
        retry_count = 0
        request_func = None
        response = None
        err_msg = None
        if debug:
            logger.info(
                f"Async request [{func_name}]: {url}, "
                f"METHOD: {method}, HEADER: {headers}, PARAMS: {params}, "
                f"DATA: {data}, JSON: {json}"
            )

        while retry_count < retries:
            try:
                # set timeout
                client_timeout = ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(
                    timeout=client_timeout
                ) as session:
                    if method == HttpMethod.POST:
                        request_func = session.post
                    elif method == HttpMethod.PUT:
                        request_func = session.put
                    elif method == HttpMethod.PATCH:
                        request_func = session.patch
                    elif method == HttpMethod.DELETE:
                        request_func = session.delete
                    else:
                        request_func = requests.get

                    async with request_func(
                        url,
                        params=params,
                        data=data,
                        json=json,
                        headers=headers,
                        auth=auth,
                    ) as response:
                        status_code = response.status
                        description = HTTPStatus(status_code).phrase
                        if status_code in success_http_code:
                            data = await response.text()
                            return True, None, data, response
                        else:
                            retry_count += 1
                            if retry_count < retries:
                                await asyncio.sleep(1)
                            else:
                                # max retries reached
                                err_msg = (
                                    f"Error status_code: {status_code},"
                                    f" description: {description}"
                                )
            except (TimeoutError, ClientError) as e:
                retry_count += 1
                if retry_count < retries:
                    await asyncio.sleep(1)
                else:
                    # max retries reached
                    err_msg = f"Connection Timeout: {e}"
        return False, err_msg, None, response

    @staticmethod
    def is_valid_url(url, schemes):
        """Check if url is valid.

        Args:
            url: url to check
            schemes: url schemes

        Returns:
            True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in schemes, result.netloc])
        except ValueError:
            return False
        return True

    @staticmethod
    def get_zip_content(zip_filepath):
        success = True
        err_msgs = []
        results = {}
        try:
            with zipfile.ZipFile(zip_filepath, "r") as zf:
                file_names = zf.namelist()
                for file_name in file_names:
                    with zf.open(file_name) as file:
                        result = file.read().decode("utf-8")
                        results[file_name] = result
        except FileNotFoundError:
            err_msgs.append("Zip file: {zip_filepath} is not found")
            success = False
        except Exception as e:
            err_msgs.append(f"Unknown error: {e}")
            success = False
        return success, err_msgs, results

    @staticmethod
    def loop_with_timeout(condition_check, timeout, interval, *args, **kwargs):
        """Wait loop with timeout.

        Args:
            condition_check: function to check condition
            timeout: timeout in seconds
            interval: interval in seconds
            args: arguments to function condition_check
            kwargs: keyword arguments to function condition_check
            *args: arguments to function condition_check
            **kwargs: keyword arguments to function condition_check

        Returns:
            True if condition met, False otherwise
        """
        err_msg = None
        start_time = time.time()
        while True:
            # check condition
            success, err_msg, result = condition_check(*args, **kwargs)
            if success:
                return True, err_msg, result

            # check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                err_msg = f"Timed out: {err_msg}"
                return False, err_msg, None

            # sleep
            time.sleep(interval)

    @staticmethod
    def get_nested_dict_value(dictionary, *keys, default=None):
        """Get nested dict value.

        Args:
            dictionary: dictionary to get value from
            keys: keys to get
            default: default value
            *keys: keys to get

        Returns:
            value from dictionary
        """
        try:
            current = dictionary
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            pass
        return default

    @staticmethod
    def run_callbacks(data, callbacks):
        """Run callbacks for job.

        Args:
            data: data to send
            callbacks: callbacks
        """
        success = True
        err_msg = None
        for callback in callbacks:
            url = callback.get("url", None)
            method = callback.get("method", HttpMethod.POST)
            headers = copy.deepcopy(HttpHeaders.DEFAULT_JSON_HEADERS)
            user_defined_headers = callback.get("headers", {})
            headers.update(user_defined_headers)
            retries = callback.get("retries", 3)
            timeout = callback.get("timeout", 10)
            if url:
                _success, err_msg, text, result = Library.call_http_api(
                    url,
                    method,
                    data=json.dumps(data),
                    func_name="run_callbacks",
                    headers=headers,
                    retries=retries,
                    timeout=timeout,
                )
                if not _success:
                    success = False
            else:
                success = False
        return success, err_msg

    @staticmethod
    async def async_run_callbacks(data, callbacks):
        """Async run callbacks for job.

        Args:
            data: data to send
            callbacks: callbacks
        """
        success = True
        err_msg = None
        if not callbacks:
            return success, err_msg
        for callback in callbacks:
            url = callback.get("url", None)
            method = callback.get("method", HttpMethod.POST)
            headers = copy.deepcopy(HttpHeaders.DEFAULT_JSON_HEADERS)
            user_defined_headers = callback.get("headers", {})
            headers.update(user_defined_headers)
            retries = callback.get("retries", 3)
            timeout = callback.get("timeout", 10)
            if url:
                (
                    _success,
                    err_msg,
                    text,
                    result,
                ) = await Library.async_call_http_api(
                    url,
                    method,
                    data=json.dumps(data, default=str),
                    func_name="run_callbacks",
                    headers=headers,
                    retries=retries,
                    timeout=timeout,
                )
                if not _success:
                    success = False
            else:
                success = False
        return success, err_msg

    @staticmethod
    def get_sorted_keys(sort_obj, sort_fields):
        """Get sorted keys from sort_obj.

        Args:
            sort_obj: object to be sorted
            sort_fields: field list to be sort

        Returns:
            sorted keys
        """
        key_tuple = []
        for field in sort_fields:
            # process descending mark (-)
            if field.startswith("-"):
                real_field = field[1:]
                reverse_flag = -1
            else:
                real_field = field
                reverse_flag = 1

            # get field value
            if isinstance(sort_obj, dict):
                value = sort_obj.get(real_field)
            else:
                value = getattr(sort_obj, real_field, None)

            # handling data type: int/float by multiplying reverse_flag
            if isinstance(value, (int, float)):
                key_tuple.append(value * reverse_flag)
            elif isinstance(value, datetime):
                # handling data type: datetime
                _value = value
                if reverse_flag != 1:
                    tzinfo = value.tzinfo
                    future_datetime = datetime(
                        2999, 12, 31, 23, 59, 59, 0, tzinfo
                    )
                    _value = future_datetime - value
                key_tuple.append(_value)
            else:
                # handling other data types
                key_tuple.append(
                    value if reverse_flag == 1 else str(value)[::-1]
                )
        return tuple(key_tuple)

    @staticmethod
    def generate_binary_combinations(bit_length, total_count):
        """Generate binary-bits combinations.

        Generate binary-bits combinations with given bit_length and assign
        random percentages

        Args:
            bit_length: length of bits
            total_count: total number of bits

        Returns:
            binary-bits combinations with random percentage
        """
        result = {}
        if bit_length <= 0:
            return result

        result_value_weight_range = (80, 100)

        # 1. generate all binary-bit combinations
        total_combinations = 2**bit_length
        combinations = [
            bin(num)[2:].zfill(bit_length) for num in range(total_combinations)
        ]

        # 2. generate random weights
        weights = [random.random() for _ in range(total_combinations)]

        # 3. calculate and assign counts to combinations
        length = len(combinations)
        first_value_count = int(
            random.randint(
                result_value_weight_range[0], result_value_weight_range[1]
            )
            * total_count
            / 100
        )
        current_total_count = 0
        i = 0
        for combo, weight in zip(combinations, weights):
            if i == 0:
                combo_count = first_value_count
            elif i == length - 1:
                combo_count = total_count - current_total_count
            else:
                combo_count = math.ceil(
                    random.randint(0, 1)
                    * (total_count - first_value_count)
                    / length
                )
                if current_total_count >= combo_count:
                    combo_count = 0
            current_total_count += combo_count
            result[combo] = combo_count
            i += 1

        # 4. remove value=0 in the result
        return {k: v for k, v in result.items() if v != 0}

    @staticmethod
    def md5_encrypt(text):
        """Encrypt text using md5.

        Args:
            text: Text to be encrypted

        Returns:
            Encrypted text
        """
        # create md5 hash object
        md5_hash = hashlib.md5()
        md5_hash.update(text.encode("utf-8"))

        # get hex hash
        encrypted_text = md5_hash.hexdigest()

        return encrypted_text

    @staticmethod
    def encrypt_text(plaintext, encryption_prefix="++", fernet_key=""):
        """Encrypt text.

        Args:
            plaintext: plain text
            encryption_prefix: encryption prefix
            fernet_key: fernet key

        Returns:
            success, error message, encrypted text
        """
        encrypted_text = None
        try:
            cipher_suite = Fernet(fernet_key)
            encoded_text = cipher_suite.encrypt(plaintext.encode()).decode(
                "utf-8"
            )
            encrypted_text = f"{encryption_prefix}{encoded_text}"
        except Exception as e:
            err_msg = f"Encryption failed. Reason: {repr(e)}"
            return False, err_msg, None
        return True, None, encrypted_text

    @staticmethod
    def decrypt_text(cipher_text, encryption_prefix="++", fernet_key=""):
        """Decrypt text.

        Args:
            cipher_text: ciphered text
            encryption_prefix: encryption prefix
            fernet_key: fernet key

        Returns:
            success, error message, decrypted text
        """
        decrypted_text = None
        if not cipher_text.startswith(encryption_prefix):
            err_msg = (
                "Decryption failed, ciphertext must starts with: "
                f"{encryption_prefix}"
            )
            return False, err_msg, None
        try:
            cipher_suite = Fernet(fernet_key)
            cipher_text = cipher_text.replace(encryption_prefix, "")
            decrypted_text = cipher_suite.decrypt(cipher_text.encode()).decode(
                "utf-8"
            )
        except Exception as e:
            err_msg = f"Decryption failed. Reason: {repr(e)}"
            return False, err_msg, None
        return True, None, decrypted_text

    @staticmethod
    def mask_password(
        configs,
        password_replace="*" * 8,
        keys_to_match=r"^(?:_.*|.*(password|secret|hidden).*)$",
    ):
        """Mask password.

        Args:
            configs: configs
            password_replace: password text to be replaced
            keys_to_match: keys to be matched (regular expression)

        Returns:
            replaced configs
        """
        configs = copy.deepcopy(configs)
        # if configs is dict
        if isinstance(configs, dict):
            new_config = {}
            for key, value in configs.items():
                # if key matches regex: keys_to_match
                regex = re.compile(keys_to_match, re.IGNORECASE)
                if regex.match(key):
                    new_config[key] = password_replace
                else:
                    # handle values recursively
                    new_config[key] = Library.mask_password(
                        value,
                        password_replace=password_replace,
                        keys_to_match=keys_to_match,
                    )
            return new_config
        # if configs is list or tuple
        elif isinstance(configs, (list, tuple)):
            # handle elements recursively
            return type(configs)(
                Library.mask_password(
                    item,
                    password_replace=password_replace,
                    keys_to_match=keys_to_match,
                )
                for item in configs
            )
        return configs

    @staticmethod
    def encrypt_virtual_instance_id(
        device_names_list, uuid_str, salt="", encode=False
    ):
        """Encrypt virtual instance id.

        Args:
            device_names_list: device name
            uuid_str: uuid string
            salt: salt
            encode: whether to encode with utf-8

        Returns:
            success, error message, virtual instance id
        """
        new_uuid = None
        try:
            device_names = "+".join(device_names_list)
            uuid_salt_str = f"{device_names}|{uuid_str}|{salt}"
            md5_hash = hashlib.md5(uuid_salt_str.encode("utf-8")).hexdigest()
            verify_code = (
                md5_hash[0] + md5_hash[1] + md5_hash[-2] + md5_hash[-1]
            )
            new_uuid = f"{device_names}|{uuid_str}|{verify_code}"
        except Exception as e:
            err_msg = f"Encryption failed. Reason: {repr(e)}"
            return False, err_msg, None

        if encode:
            new_uuid = base64.b64encode(new_uuid.encode("utf-8")).decode(
                "utf-8"
            )
        return True, None, new_uuid

    @staticmethod
    def decrypt_virtual_instance_id(
        virtual_instance_id, salt="", encode=False
    ):
        """Decrypt virtual instance id.

        Args:
            virtual_instance_id: virtual instance id
            salt: salt
            encode: whether to encode with utf-8

        Returns:
            success, error message, device_names, instance_id
        """
        err_msg = None
        try:
            if encode is True:
                virtual_instance_id = base64.b64decode(
                    virtual_instance_id
                ).decode("utf-8")

            # split virtual_instance_id
            first = virtual_instance_id.index("|")
            last = virtual_instance_id.rindex("|")

            device_names = virtual_instance_id[:first]
            device_names_list = device_names.split("+")
            instance_id = virtual_instance_id[first + 1 : last]
            actual_verify_code = virtual_instance_id[last + 1 :]

            uuid_salt_str = f"{device_names}|{instance_id}|{salt}"
            md5_hash = hashlib.md5(uuid_salt_str.encode("utf-8")).hexdigest()
            expect_verify_code = (
                md5_hash[0] + md5_hash[1] + md5_hash[-2] + md5_hash[-1]
            )

            if actual_verify_code == expect_verify_code:
                return True, err_msg, device_names_list, instance_id

            err_msg = "Decryption failed. Reason: Unauthorized"
            return False, err_msg, None, None
        except Exception as e:
            err_msg = f"Decryption failed. Reason: {repr(e)}"
            return False, err_msg, None, None

    @staticmethod
    async def job_callback(flow, flow_run, state, results=None):
        """Job callback.

        Args:
            flow: flow
            flow_run: flow run
            state: flow state
            results: flow results
        """
        job_id = flow_run.name  # use name as job uuid
        job_status = Constant.JOB_STATUS_COMPLETED
        is_failed = False
        flow_state_name = state.name.upper()
        parameters = flow_run.parameters
        error_results = None
        callback_success = True
        callbacks = Library.get_nested_dict_value(
            parameters, "job_info", "data", "callbacks", default=None
        )
        backend = Library.get_nested_dict_value(
            parameters, "job_info", "data", "backend", default=None
        )

        if not callbacks:
            return

        if flow_state_name in Constant.PREFECT_WAIT_STATES:
            return

        if flow_state_name in [
            Constant.PREFECT_STATE_RUNNING,
            Constant.PREFECT_STATE_COMPLETED,
        ]:
            if results is None:
                results = await flow_run.state.result()
        else:
            error_details = None
            results = None
            is_failed = True
            if flow_state_name == Constant.PREFECT_STATE_CANCELLING:
                job_status = Constant.JOB_STATUS_CANCELLED
            try:
                await flow_run.state.result()
            except Exception as e:
                error_details = f"{e.__class__.__name__}: {str(e)}"

            error_results = {
                "code": -HttpCode.INTERNAL_SERVER_ERROR,
                "message": "[JOB] Running failed in job engine",
                "data": {"details": error_details},
            }

        if results:
            for result in results:
                status = Library.get_nested_dict_value(
                    result, "metadata", "status", default=None
                )
                if status != Constant.JOB_STATUS_COMPLETED:
                    is_failed = True
                _callback_success = Library.get_nested_dict_value(
                    result, "metadata", "callback_success", default=False
                )
                if not _callback_success:
                    callback_success = False

        if not callback_success:
            # run callbacks
            # if job_info contains callback list and driver is in sync mode
            # run async callback
            if is_failed:
                job_status = Constant.JOB_STATUS_FAILED

            data = {
                "job_id": job_id,
                "job_status": job_status,
                "backend": backend,
            }
            if results:
                data["results"] = results
            if error_results:
                data["error"] = error_results

            success, err_msg = await Library.async_run_callbacks(
                data, callbacks
            )
            if success:
                for result in results:
                    result["metadata"]["callback_success"] = True
            else:
                logger.error(f"Callback Error: {err_msg}")

            return results


def _s(secret):
    """Secret text wrapper.

    Args:
        secret: secret text to be wrapped

    Returns:
        wrapped secret text
    """
    return secret
