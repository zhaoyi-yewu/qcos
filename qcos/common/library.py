#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import fnmatch
import importlib
import inspect
import logging
import os
import pkgutil
import re
import requests
import time
import tomlkit
import zipfile
from datetime import datetime
from schema import Schema
from urllib.parse import urlparse
from uuid import UUID

from .constant import HttpMethod


logger = logging.getLogger(__name__)


class Library:
    """
    Library
    """
    @staticmethod
    def create_pid_file(file_path):
        """
        Crete pid file

        :param file_path: file path
        """
        try:
            pid = os.getpid()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(pid))
        except Exception as e:
            print(f"Unable to create pid file: {file_path}\n{e}")

    @staticmethod
    def find_dirs(base_dir="/", pattern="*", recursive=False):
        """
        Find all dirs

        :param base_dir: base dir to search
        :param pattern: match pattern
        :param recursive: recursive search
        :return: dir list
        """
        dirs = []
        if os.path.isdir(base_dir):
            dirs.append(base_dir)
            if recursive:
                for root, dir_names, filenames in os.walk(base_dir):
                    for dir_name in fnmatch.filter(dir_names, pattern):
                        _dir_name = os.path.join(root, dir_name)
                        if _dir_name not in dirs:
                            dirs.append(_dir_name)
        return dirs

    @staticmethod
    def find_files(base_dir, pattern="*", recursive=False, exclusives=None):
        """
        Find files under given dir

        :param base_dir: base dir to search
        :param pattern: match pattern
        :param recursive: recursive search
        :param exclusives: filename to exclude
        :return: file list
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
    def mkdir(dir_name):
        """
        Create dir

        :param dir_name: dir name
        :return: True or False
        """
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            return True
        return False

    @staticmethod
    def mkdirs(dir):
        """
        Create dirs

        :param dir: dir name
        """
        sub_path = os.path.dirname(dir)
        if not os.path.exists(sub_path):
            Library.mkdirs(sub_path)
        if not os.path.exists(dir):
            os.mkdir(dir)

    @staticmethod
    def rm_file(file):
        """
        remove file

        :param file: file path
        :return: True or False
        """
        if os.path.isfile(file):
            try:
                os.remove(file)
            except Exception as e:
                pass
        return True

    @staticmethod
    def import_classes(
            pkg_dir, base_module_name="drivers", base_dir=None,
            base_class=None):
        """
        Import class from package dir

        :param pkg_dir: package dir
        :param base_module_name: base module name
        :param base_dir: base dir
        :param base_class: base class
        :return: class dict
        """
        classes = {}
        for (module_loader, name, is_pkg) in pkgutil.iter_modules([pkg_dir]):
            module_path = module_loader.path.replace(base_dir, "")
            module_name = (f"{base_module_name}"
                           f"{module_path.replace('/', '.')}.{name}")
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    if issubclass(obj, base_class) and obj != base_class:
                        classes[obj.__name__] = obj
        return classes

    @staticmethod
    def str_match(str, regex, ignore_case=False):
        """
        Match string with regex

        :param str: string
        :param regex: regex pattern
        :param ignore_case: ignore case
        :return: bool
        """
        if ignore_case:
            reg = re.compile(regex, re.IGNORECASE)
        else:
            reg = re.compile(regex)
        if reg.findall(str):
            return True
        return False

    @staticmethod
    def read_toml_file(file_path: str):
        """
        Read toml file

        :param file_path: toml file path
        :return: success, err_msg, toml dict
        """
        try:
            with open(file_path, 'rb') as _file:
                return True, None, tomlkit.load(_file)
        except FileNotFoundError:
            return False, f"file: {file_path} does not exist", None
        except Exception as e:
            return False, f"toml parser exception: {e}", None

    @staticmethod
    def write_to_toml(data: dict, file_path: str):
        """
        Write dict to toml file

        :param data: data
        :param file_path: file_path
        :return: success, err_msg
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                tomlkit.dump(data, file)
            return True, None
        except Exception as e:
            return False, f"failed to write toml file: {file_path}. {e}"

    @staticmethod
    def get_current_datetime():
        """
        Get current datetime

        :return: datetime
        """
        return datetime.now()

    @staticmethod
    def validate_values_enum(value, argument_name, value_list,
                             allow_none=False):
        """
        Validate values for enum

        :param value: value
        :param argument_name: argument name
        :param value_list: valid value list
        :param allow_none: allow None value
        :return: True or False
        """
        if not value and allow_none:
            return True, None
        if value not in value_list:
            return (False, [
                f"Invalid argument: {argument_name}={value}. "
                f"reason: valid values: {', '.join(value_list)}"])
        return True, None

    @staticmethod
    def validate_values_uuid(value, argument_name):
        """
        Validate values for uuid

        :param value: value
        :param argument_name: argument name
        :return: True or False
        """
        try:
            uuid_obj = UUID(value, version=4)
            if str(uuid_obj) != value:
                return (False, [f"Invalid argument: {argument_name}={value}. "
                                f"reason: UUID version error"])
        except ValueError:
            return (False, [f"Invalid argument: {argument_name}={value}. "
                            f"reason: UUID value error"])
        return True, None

    @staticmethod
    def validate_values_range(
            value, argument_name, min_value=None, max_value=None):
        """
        Validate values for int range

        :param value: value
        :param argument_name: argument name
        :param min_value: minimum value
        :param max_value: maximum value
        :return: True or False
        """
        err_msgs = []
        if min_value:
            if value < min_value:
                err_msgs.append(f"Invalid argument: {argument_name}={value}. "
                                f"reason: value should >= {min_value}")
        if max_value:
            if value > max_value:
                err_msgs.append(f"Invalid argument: {argument_name}={value}. "
                                f"reason: value should <= {max_value}")
        if err_msgs:
            return False, err_msgs
        return True, None

    @staticmethod
    def validate_values_length(
            value, argument_name, min_value=None, max_value=None,
            allow_none=False):
        """
        Validate values for int range

        :param value: value
        :param argument_name: argument name
        :param min_value: minimum value
        :param max_value: maximum value
        :param allow_none: allow None value
        :return: True or False
        """
        err_msgs = []
        if not value and allow_none:
            return True, err_msgs
        if min_value:
            if len(value) < min_value:
                err_msgs.append(
                    f"Invalid argument: {argument_name}={value}. "
                    f"reason: length of value should >= {min_value}")
        if max_value:
            if len(value) > max_value:
                err_msgs.append(
                    f"Invalid argument: {argument_name}={value}. "
                    f"reason: length of value should <= {max_value}")
        if err_msgs:
            return False, err_msgs
        return True, None

    @staticmethod
    def validate_values_list(value, argument_name, value_type,
                             allow_none=False):
        """
        Validate values for list

        :param value: value
        :param argument_name: argument name
        :param value_type: data type of value
        :param allow_none: allow None value
        :return: True or False
        """
        if not isinstance(value, list):
            return (False, [f"Invalid argument: {argument_name}={value}. "
                            f"reason: type: list is required"])
        for _value in value:
            if not isinstance(_value, value_type):
                return (False, [f"Invalid argument: {argument_name}={value}. "
                                f"reason: valid list element value type: "
                                f"{value_type}"])
            if not allow_none and not _value:
                return (False, [
                    f"Invalid argument: {argument_name}={value}. "
                    f"reason: None or empty element in list is not allowed"])
        return True, None

    @staticmethod
    def validate_schema(value, schema_obj):
        """
        Validate schema values

        :param value: value to be validated
        :param schema_obj: schema obj
        :return: None if success or error message
        """
        err_msg = None
        try:
            _schema = Schema(schema_obj)
            _schema.validate(value)
        except Exception as e:
            err_msg = str(e)
        return err_msg

    @staticmethod
    def call_http_api(
            url, method, *,
            data=None, json=None, files=None, params=None, func_name=None,
            headers=None, auth=None, verify_ssl=False,
            retry=1, timeout=10, success_http_code=[200],
            debug=False):
        """
        Call http api

        :param url: api url
        :param method: http method
        :param data: data for http body
        :param json: json data for http body
        :param files: files for http body
        :param params: params for http url
        :param func_name: function name
        :param headers: http headers
        :param auth: http auth
        :param verify_ssl: if verify ssl certificate
        :param retry: times to retry if failed
        :param timeout: timeout in seconds
        :param success_http_code: success http status
        :param debug: enable or disable debug
        """
        request_func = None
        r = None
        if debug:
            logger.info(
                f"Request [{func_name}]: {url}, "
                f"METHOD: {method}, HEADER: {headers}, PARAMS: {params}, "
                f"DATA: {data}, JSON: {json}")
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

        for i in range(1, retry + 1):
            r = request_func(
                url,
                headers=headers,
                params=params,
                data=data,
                files=files,
                json=json,
                auth=auth,
                verify=verify_ssl,
                timeout=timeout
            )
            if r.status_code in success_http_code:
                break
        return r.status_code, r.reason, r.text, r

    @staticmethod
    def is_valid_url(url, schemes):
        """
        Check if url is valid

        :param url: url to check
        :param schemes: url schemes
        :return: True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([
                result.scheme in schemes,
                result.netloc
            ])
        except ValueError:
            return False
        return True

    @staticmethod
    def get_zip_content(zip_filepath):
        success = True
        err_msgs = []
        results = {}
        try:
            with zipfile.ZipFile(zip_filepath, 'r') as zf:
                file_names = zf.namelist()
                for file_name in file_names:
                    with zf.open(file_name) as file:
                        result = file.read().decode('utf-8')
                        results[file_name] = result
        except FileNotFoundError:
            err_msgs.append("Zip file: {zip_filepath} is not found")
            success = False
        except Exception as e:
            err_msgs.append(f"Unknown error: {e}")
            success = False
        return success, err_msgs, results

    @staticmethod
    def loop_with_timeout(condition_check, timeout, interval,
                          *args, **kw_args):
        """
        Wait loop with timeout

        :param condition_check: function to check condition
        :param timeout: timeout in seconds
        :param interval: interval in seconds
        :param args: arguments to function condition_check
        :param kw_args: keyword arguments to function condition_check
        :return: True if condition met, False otherwise
        """
        err_msg = None
        start_time = time.time()
        while True:
            # check condition
            result = condition_check(*args, **kw_args)
            if result:
                return True, err_msg, result

            # check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                err_msg = "Timed out"
                return False, err_msg, None

            # sleep
            time.sleep(interval)
