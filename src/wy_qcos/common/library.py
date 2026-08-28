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

import aiohttp
import asyncio
import base64
import copy
import csv
import ctypes
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
import psutil
import random
import re
import requests
import signal
import socket
import sys
import tempfile
import time
import tomlkit
import uuid
import zipfile

from aiohttp import ClientTimeout, ClientError
from collections import OrderedDict
from cryptography.fernet import Fernet
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from schema import Schema
from urllib.parse import urlparse

from . import args_schema
from .constant import HttpCode, HttpHeaders, HttpMethod, Constant

logger = logging.getLogger(__name__)

# Allowed module name prefixes for dynamic imports (security whitelist).
# Matching uses dot-boundary semantics: "wy_qcos." matches "wy_qcos.foo"
# but NOT "wy_qcos_evil".
_ALLOWED_MODULE_PREFIXES = ("wy_qcos",)

# Regex restricting module name format to letters, digits, underscores and
# dots, starting with a letter or underscore (security validation).
_ALLOWED_MODULE_NAME_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_.]*")

# Regex restricting class name format to valid Python identifiers,
# rejecting dunder/magic attributes (security validation).
_ALLOWED_CLASS_NAME_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

# Cached libc handle for malloc_trim (Linux/glibc only). Loaded lazily
# on first load_libc() call; None on non-Linux platforms or when
# malloc_trim is not exported by libc.
_libc_handle = None
_libc_loaded = False


def _is_allowed_module(module_name):
    """Check whether a module name is in the allowed import whitelist.

    Performs two layers of validation:
      1. format check via regex (only letters, digits, underscores, dots)
      2. prefix check against the allowed import whitelist using
         dot-boundary matching to prevent prefix-confusion attacks
         (e.g. "wy_qcos_evil" must not match prefix "wy_qcos")

    Args:
        module_name: fully qualified module name

    Returns:
        True if the module name passes both format and whitelist checks
    """
    if not module_name:
        return False
    if not _ALLOWED_MODULE_NAME_RE.fullmatch(module_name):
        return False
    # dot-boundary prefix match: the module name must either equal an
    # allowed prefix exactly or start with "<prefix>."
    for prefix in _ALLOWED_MODULE_PREFIXES:
        if module_name == prefix or module_name.startswith(prefix + "."):
            return True
    return False


def _is_allowed_class_name(class_name):
    """Check whether a class name is safe for dynamic getattr.

    Performs validation:
      1. non-empty string
      2. format check via regex (valid Python identifier)
      3. reject dunder/magic attributes (names starting with "__")
         to prevent access to dangerous attributes like __builtins__,
         __import__, __subclasses__, etc.

    Args:
        class_name: attribute name to validate

    Returns:
        True if the class name is safe for dynamic attribute access
    """
    if not class_name:
        return False
    if not _ALLOWED_CLASS_NAME_RE.fullmatch(class_name):
        return False
    # reject dunder attributes to prevent magic attribute abuse
    if class_name.startswith("__"):
        return False
    return True


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
    def kill_pid(pid_file, expected_process_name=None, allow_kill_self=False):
        """Kill existing process from pid file.

        Args:
            pid_file: pid file path
            expected_process_name: expected process name in regular expression
            allow_kill_self: allow kill current process
        """
        pid = None
        need_to_kill = True
        if not os.path.exists(pid_file):
            return
        try:
            # Read and validate PID file content
            with open(pid_file, encoding="utf-8") as f:
                pid_str = f.read().strip()
                if not pid_str.isdigit():
                    raise ValueError(f"Invalid pid format: {pid_str}")
                pid = int(pid_str)
            # match expected process name
            if expected_process_name and pid:
                cmd_line = None
                cmd_line_filepath = f"/proc/{pid}/cmdline"
                if os.path.exists(cmd_line_filepath):
                    with open(cmd_line_filepath) as f:
                        cmd_line = f.read().replace("\0", " ").strip()
                    if not Library.str_match(cmd_line, expected_process_name):
                        need_to_kill = False
            if not allow_kill_self:
                if os.getpid() == pid:
                    need_to_kill = False
            # Attempt to terminate the process by sending SIGTERM signal.
            # Poll for up to 10 seconds for the process to exit; if it is
            # still alive, escalate to SIGKILL to ensure the port is
            # released before the new process starts.
            if pid and need_to_kill:
                os.kill(pid, signal.SIGTERM)
                # Wait for process to exit with escalating timeout
                max_wait = 10
                waited = 0
                while waited < max_wait:
                    try:
                        # os.kill with signal 0 checks process existence
                        os.kill(pid, 0)
                        time.sleep(0.5)
                        waited += 0.5
                    except ProcessLookupError:
                        # Process has exited
                        break
                if waited >= max_wait:
                    # Process did not exit gracefully; force kill
                    try:
                        os.kill(pid, signal.SIGKILL)
                        time.sleep(0.5)
                    except ProcessLookupError:
                        pass
                    print(
                        f"Process {pid} did not exit after SIGTERM "
                        f"within {max_wait}s, sent SIGKILL"
                    )
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
    def is_file(file_path):
        """Is file.

        Args:
            file_path: file path
        """
        return os.path.isfile(file_path)

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
    def get_top_dir():
        return str(Path(__file__).resolve().parent.parent.parent.parent)

    @staticmethod
    def load_libc():
        """Load libc (Linux/glibc only) and cache the handle.

        Returns the libc CDLL handle when libc.so.6 is available and
        exports malloc_trim; returns None on non-Linux platforms or
        when malloc_trim is not present. The result is cached so
        repeated calls do not reload the library.

        Returns:
            ctypes.CDLL handle or None
        """
        global _libc_handle, _libc_loaded
        if _libc_loaded:
            return _libc_handle
        _libc_loaded = True
        try:
            _libc_handle = ctypes.CDLL("libc.so.6", use_errno=True)
            if not hasattr(_libc_handle, "malloc_trim"):
                logger.debug(
                    "libc does not export malloc_trim; "
                    "skipping malloc_trim calls"
                )
                _libc_handle = None
        except OSError:
            logger.debug(
                "libc.so.6 not available (non-Linux platform); "
                "skipping malloc_trim calls"
            )
            _libc_handle = None
        return _libc_handle

    @staticmethod
    def malloc_trim(pad=0):
        """Call glibc malloc_trim to release free heap memory to the OS.

        malloc_trim(pad) asks glibc to return free memory at the top of
        the heap back to the OS, keeping at least ``pad`` bytes. This
        is a no-op on non-glibc platforms.

        Args:
            pad: number of bytes to retain at the top of the heap

        Returns:
            1 on success, 0 on failure, or None when malloc_trim is
            not available
        """
        libc = Library.load_libc()
        if libc is None:
            return None
        return libc.malloc_trim(pad)

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
    def get_processes(regex_list):
        """Get processes.

        Args:
            regex_list: regex list to match
        """
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                for regex in regex_list:
                    if Library.str_match(cmdline, regex):
                        processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    @staticmethod
    def kill(process_list, force: bool = False):
        """Kill processes.

        Args:
            process_list: processes
            force: force to kill

        Returns:
            pids that are killed successfully, pids that are failed to kill
        """
        success_pids = []
        failed_pids = []

        for proc in process_list:
            pid = proc.pid
            try:
                if force:
                    # force to kill
                    proc.kill()
                else:
                    # terminate processes gracefully
                    proc.terminate()
                # wait process to exit
                gone, alive = psutil.wait_procs([proc], timeout=5)
                if not alive:
                    success_pids.append(pid)
                else:
                    # failed to terminate processes gracefully, force to kill
                    proc.kill()
                    psutil.wait_procs([proc], timeout=2)
                    success_pids.append(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                failed_pids.append((pid, str(e)))

        return success_pids, failed_pids

    @staticmethod
    def get_venv_dirs(venv_base_dir, default_venv_dir="default"):
        """Get venv dirs.

        Args:
            venv_base_dir: base directory to search for virtual environments
            default_venv_dir: default venv dir name

        Returns:
            list: list of venv directory paths that contain activate file
        """
        venv_dirs = OrderedDict()

        # check if venv base dir exists
        if not os.path.exists(venv_base_dir):
            return venv_dirs

        # check if venv_base_dir is dir
        if not os.path.isdir(venv_base_dir):
            return venv_dirs

        try:
            for _dir in os.listdir(venv_base_dir):
                driver_name = _dir
                driver_dir = os.path.join(venv_base_dir, _dir)
                driver_bin_dir = os.path.join(driver_dir, "bin")
                if os.path.isdir(driver_bin_dir):
                    for root, dirs, files in os.walk(driver_bin_dir):
                        if "activate" in files:
                            if driver_dir not in venv_dirs:
                                venv_dirs[driver_name] = {}
                            venv_dirs[driver_name]["driver_dir"] = driver_dir
                            break
                driver_lib_dir = os.path.join(driver_dir, "lib")
                if os.path.isdir(driver_lib_dir):
                    for root, dirs, files in os.walk(driver_lib_dir):
                        for _dir in dirs:
                            if "site-packages" != _dir:
                                continue
                            if driver_dir not in venv_dirs:
                                venv_dirs[driver_name] = {}
                            site_packages_dir = os.path.join(root, _dir)
                            venv_dirs[driver_name]["site_packages"] = (
                                site_packages_dir
                            )
                            break
        except (OSError, PermissionError) as e:
            logger.error(f"Error scanning venv directories: {e}")

        if default_venv_dir and default_venv_dir in venv_dirs:
            # reorder venv_dirs
            default_venv_info = venv_dirs.pop(default_venv_dir)
            venv_dirs[default_venv_dir] = default_venv_info

        return venv_dirs

    @staticmethod
    def set_venv_path(venv_base_dir):
        """Set venv path.

        Args:
            venv_base_dir: venv base dir
        """
        venv_dirs = Library.get_venv_dirs(venv_base_dir)
        for venv_name, venv_dir_info in venv_dirs.items():
            venv_site_packages_dir = venv_dir_info["site_packages"]
            if os.path.isdir(venv_site_packages_dir):
                sys.path.insert(0, venv_site_packages_dir)

    @staticmethod
    def set_driver_venv_path(driver_name, venv_base_dir):
        """Set driver venv path.

        Args:
            driver_name: driver name
            venv_base_dir: venv base dir

        Returns:
            original sys.path
        """
        sys_path = copy.deepcopy(sys.path)
        _, python_path_env = Library.get_driver_venv(
            driver_name, venv_base_dir
        )
        python_path = python_path_env["PYTHONPATH"]
        if python_path and ":" in python_path:
            for site_packages_dir in python_path.split(":")[::-1]:
                sys.path.insert(0, site_packages_dir)
        return sys_path

    @staticmethod
    def get_driver_venv(driver_name, venv_dir, add_default_env=True):
        """Get driver venv.

        Args:
            driver_name: driver name
            venv_dir: venv dir
            add_default_env: if add default env

        Returns:
            python_bin, python_path_env
        """
        python_paths = []
        default_python_bin = "python3"
        python_bin = default_python_bin
        default_python_path = os.environ.get("PYTHONPATH", None)
        default_venv_dir = f"{venv_dir}/default"
        default_venv_python_path = (
            f"{default_venv_dir}/lib/python3.11/site-packages/"
        )

        _python_bin = f"{venv_dir}/{driver_name}/bin/python3"
        if Library.is_file(_python_bin):
            python_bin = _python_bin
            venv_python_path = (
                f"{venv_dir}/{driver_name}/lib/python3.11/site-packages/"
            )
            python_paths.append(venv_python_path)
        else:
            _python_bin = f"{default_venv_dir}/bin/python3"
            if Library.is_file(_python_bin):
                python_bin = _python_bin

        if add_default_env:
            # add default venv python path
            if default_venv_python_path not in python_paths:
                python_paths.append(default_venv_python_path)
            # add default python path
            if default_python_path and default_python_path not in python_paths:
                python_paths.append(default_python_path)
        python_path_env = {"PYTHONPATH": ":".join(python_paths)}
        return python_bin, python_path_env

    @staticmethod
    def import_classes(
        pkg_dir,
        base_module_name="drivers",
        base_dir=None,
        base_class=None,
        excluded_class=None,
        venv_base_dir=None,
        venv_loader=None,
    ):
        """Import class from package dir.

        Args:
            pkg_dir: package dir
            base_module_name: base module name (Default value = "drivers")
            base_dir: base dir (Default value = None)
            base_class: base class (Default value = None)
            excluded_class: excluded class (Default value = None)
            venv_base_dir: venv base dir
            venv_loader: venv loader

        Returns:
            class dict, venv_dirs
        """
        classes = {}
        venv_dirs = {}

        if venv_loader:
            # set sys.path
            orig_sys_path = copy.deepcopy(sys.path)

        for module_loader, name, is_pkg in pkgutil.iter_modules([pkg_dir]):
            module_path = module_loader.path.replace(base_dir, "")
            # normalize path separators so module names use dots on
            # both POSIX (/) and Windows (\) platforms
            module_rel_path = module_path.replace(os.sep, ".").replace(
                "/", "."
            )
            module_name = f"{base_module_name}{module_rel_path}.{name}"

            if venv_loader:
                sys.path = copy.deepcopy(orig_sys_path)
                skip, python_bin, python_path = venv_loader(
                    name, venv_base_dir
                )
                if skip:
                    continue
                if python_path and ":" in python_path:
                    for site_packages_dir in python_path.split(":")[::-1]:
                        sys.path.insert(0, site_packages_dir)

            try:
                # security: only allow importing modules under
                # whitelisted prefixes to prevent arbitrary code import
                if not _is_allowed_module(module_name):
                    raise ValueError(
                        f"Module '{module_name}' is not in the "
                        f"allowed import whitelist"
                    )
                _import_module = importlib.import_module  # security issue
                module = _import_module(module_name)
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
        if venv_base_dir:
            sys.path = copy.deepcopy(orig_sys_path)

        return classes, venv_dirs

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
        if not file_path:
            return False, "file_path cannot be empty"
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                tomlkit.dump(data, file)
            return True, None
        except Exception as e:
            return False, f"failed to write toml file: {file_path}. {e}"

    @staticmethod
    def get_current_datetime(timestamp=False):
        """Get current datetime.

        Args:
            timestamp: return timestamp

        Returns:
            datetime
        """
        datetime_now = datetime.now()
        if timestamp:
            return datetime_now.timestamp()
        return datetime_now

    @staticmethod
    def to_iso(timestamp):
        """Convert timestamp to ISO format.

        Args:
            timestamp: timestamp

        Returns:
            datetime object in ISO format
        """
        if timestamp is None:
            return None
        dt_obj = datetime.fromtimestamp(timestamp)
        return dt_obj.isoformat()

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
                    f"reason: Invalid UUID version"
                )
                return False, [err_msg]
        except ValueError:
            err_msg = (
                f"Invalid params: {param_name}={value}. reason: Invalid UUID"
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
    def validate_name(name):
        """Validate name.

        Args:
            name: name

        Returns:
            success of failed (bool), error message list
        """
        return Library.validate_schema(
            name, args_schema.NAME_SCHEMA, allow_none=True
        )

    @staticmethod
    def convert_schema(schema_dict):
        """Convert schema dict into standard schema.

        Args:
            schema_dict: schema dict

        Returns:
            standard schema dict
        """
        std_schema_dict = {}
        for _, value in schema_dict.items():
            k, v = value
            std_schema_dict[k] = v
        return std_schema_dict

    @staticmethod
    def count_qubits_in_qasm(qasm_content: str) -> int:
        """Count the number of qubits declared in QASM content.

        Supports both OpenQASM 2.0 and 3.0 declarations:
        - qreg <name>[<size>];        (OpenQASM 2.0)
        - qubit[<size>] <name>;       (OpenQASM 3.0 array form)
        - qubit <name>;               (OpenQASM 3.0 single qubit)

        Args:
            qasm_content: QASM source code string

        Returns:
            total number of declared qubits; 0 when no declaration
            is found or the input is empty.
        """
        if not qasm_content:
            return 0
        total_qubits = 0
        # qreg <name>[<size>];  (OpenQASM 2.0)
        qreg_matches = re.findall(r"qreg\s+\w+\[(\d+)\]", qasm_content)
        total_qubits += sum(int(n) for n in qreg_matches)
        # qubit[<size>] <name>;  (OpenQASM 3.0 array form)
        qubit_arr_matches = re.findall(r"qubit\[(\d+)\]\s+\w+", qasm_content)
        total_qubits += sum(int(n) for n in qubit_arr_matches)
        # qubit <name>;  (OpenQASM 3.0 single qubit, avoid matching
        # the array form qubit[<size>] already counted above)
        single_matches = re.findall(
            r"(?<![\w\[])\bqubit\s+\w+\s*;", qasm_content
        )
        # subtract single-qubit declarations that are actually part
        # of qubit[<size>] form (contains '[' between qubit and name)
        single_count = 0
        for match in single_matches:
            if "[" not in match:
                single_count += 1
        total_qubits += single_count
        return total_qubits

    @staticmethod
    def get_max_qubits_from_source_code(
        source_code: list, code_type: str = ""
    ) -> int:
        """Get the maximum qubit count across all source code items.

        Only QASM code types (qasm/qasm2/qasm3) are parsed; for other
        code types (e.g. qubo) or empty input, 0 is returned.

        Args:
            source_code: list of source code strings
            code_type: code type string (qasm, qasm2, qasm3, qubo)

        Returns:
            maximum qubit count among all source code items
        """
        if not source_code:
            return 0
        # only QASM code types declare qubits via qreg/qubit statements
        qasm_types = set(Constant.CODE_TYPES_ALL_QASM)
        if code_type and code_type not in qasm_types:
            return 0
        max_qubits = 0
        for item in source_code:
            if not isinstance(item, str):
                continue
            count = Library.count_qubits_in_qasm(item)
            if count > max_qubits:
                max_qubits = count
        return max_qubits

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
                    f"The matrix with index {i} has {matrix_shape[0]} "
                    f"qubits, exceeding the maximum limit of "
                    f"{Constant.MAX_QUBO_QUBITS}"
                )
        return True, None

    @staticmethod
    def is_valid_bitstring_dict(input_dict):
        """Check is valid bitstring dict.

        Args:
            input_dict: input dict

        Returns:
            True or False
        """
        # check input is dict
        if input_dict is None:
            return False
        if not isinstance(input_dict, dict):
            return False
        binary_re = re.compile(r"^[01]+$")
        for key in input_dict:
            # check key is binary string
            if not isinstance(key, str) or not binary_re.match(key):
                return False
            # check value is int
            if not isinstance(input_dict[key], int):
                return False
        return True

    @staticmethod
    def validate_results(result_type, results):
        """Validate results.

        Args:
            result_type: result type
            results: results

        Returns:
            success, err_msg
        """
        if not result_type or result_type not in Constant.RESULT_TYPES:
            return False, f"Invalid result_type: {result_type}"

        if result_type == Constant.RESULT_TYPE_SAMPLING:
            if not Library.is_valid_bitstring_dict(results):
                return False, (
                    f"Invalid result: {results}, "
                    "value type: 'bitstring dict' is expected"
                )
        elif result_type == Constant.RESULT_TYPE_ESTIMATION:
            if not isinstance(results, float):
                return False, (
                    f"Invalid result: {results}, "
                    "value type: 'float' is expected"
                )
        elif result_type == Constant.RESULT_TYPE_TEXT:
            if not isinstance(results, str):
                return False, (
                    f"Invalid result: {results}, "
                    "value type: 'string' is expected"
                )
        elif result_type == Constant.RESULT_TYPE_DICT:
            if not isinstance(results, dict):
                return False, (
                    f"Invalid result: {results}, "
                    "value type: 'dict' is expected"
                )
        return True, None

    @staticmethod
    def wait_network_connection(
        host,
        port=80,
        protocol="tcp",
        interval=5,
        retries=10,
        socket_timeout=10,
        timeout=60,
    ):
        """Wait until network connection to host:port is available.

        Repeatedly attempts to establish a connection to the given
        host and port until it succeeds, the global timeout is
        reached, or retries are exhausted.

        For TCP, a full connection handshake is attempted. For UDP, a
        probe datagram is sent and the method waits for any response
        within the socket timeout window to confirm reachability.

        Args:
            host: target host
            port: target port, default 80
            protocol: connection protocol, "tcp" or "udp"
            interval: seconds between retries, default 5
            retries: max retry count, default 10
            socket_timeout: socket connect/recv timeout in seconds,
                default 10
            timeout: global wall-clock timeout in seconds for the
                whole wait loop, default 60

        Returns:
            True if connection established, False otherwise
        """
        proto = protocol.lower()
        if proto not in ("tcp", "udp"):
            logger.warning(
                f"Unsupported protocol: {protocol}, fallback to tcp"
            )
            proto = "tcp"

        sock_type = socket.SOCK_STREAM if proto == "tcp" else socket.SOCK_DGRAM

        start_time = time.time()
        for attempt in range(1, retries + 1):
            # check global wall-clock timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.error(
                    f"Timed out ({timeout}s) while waiting for network "
                    f"connection to {host}:{port} ({proto})"
                )
                return False

            sock = None
            try:
                sock = socket.socket(socket.AF_INET, sock_type)
                sock.settimeout(socket_timeout)
                sock.connect((host, port))

                if proto == "tcp":
                    sock.close()
                else:
                    # UDP: send a probe and wait for any response
                    sock.sendto(b"\x00", (host, port))
                    sock.recvfrom(1024)
                    sock.close()

                logger.info(
                    f"Network connection to {host}:{port} "
                    f"({proto}) established after {attempt} attempt(s)"
                )
                return True
            except (socket.error, OSError) as e:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:  # noqa: S110
                        pass
                logger.debug(
                    f"Attempt {attempt}/{retries} failed to "
                    f"connect to {host}:{port} ({proto}): {e}"
                )
                if attempt < retries:
                    time.sleep(interval)

        logger.error(
            f"Failed to establish network connection to "
            f"{host}:{port} ({proto}) after {retries} retries"
        )
        return False

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
            success_http_code: success http status (Default value = 200)
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
            try:
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
            except Exception as e:
                logger.debug(f"HttpMethod exception info: {e}")
        if r is None:
            return HttpCode.TIMEOUT_ERROR, "Connection failed", None, None
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
    def loop_with_timeout(
        condition_check, timeout, interval, *args, max_attempts=0, **kwargs
    ):
        """Wait loop with timeout.

        Args:
            condition_check: function to check condition
            timeout: timeout in seconds
            interval: interval in seconds
            *args: arguments to function condition_check
            max_attempts: max attempt count, 0 means unlimited
            **kwargs: keyword arguments to function condition_check

        Returns:
            True if condition met, False otherwise
        """
        err_msg = None
        start_time = time.time()
        attempt_count = 0
        while True:
            attempt_count += 1

            # check condition
            success, err_msg, result = condition_check(*args, **kwargs)
            if success:
                return True, err_msg, result

            # check max attempts
            if max_attempts > 0 and attempt_count >= max_attempts:
                err_msg = (
                    f"Max attempts ({max_attempts}) reached. "
                    f"Last error: {err_msg}"
                )
                return False, err_msg, None

            # check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                err_msg = f"Timed out. Last error: {err_msg}"
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
                status_code, err_msg, text, result = Library.call_http_api(
                    url,
                    method,
                    data=json.dumps(data),
                    func_name="run_callbacks",
                    headers=headers,
                    retries=retries,
                    timeout=timeout,
                )
                if status_code != HttpCode.SUCCESS_OK:
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
    def mask_password_from_pydantic(data_obj, mask_value="*" * 8):
        """Mask password from Pydantic model.

        - sensitive=True: replace entire field with mask_value
        - db_connection_url=True: mask password in URL
        - no marker: return original value

        Args:
            data_obj: Pydantic data object
            mask_value: Mask value, default "********"

        Returns:
            dict: Dictionary with masked sensitive values
            (original dict unchanged)
        """
        try:
            # Check if data_obj is None or not a Pydantic model
            if data_obj is None:
                return {}

            # Get dictionary from Pydantic model
            data_dict = data_obj.model_dump()

            # Deep copy to avoid modifying original data
            masked_data = copy.deepcopy(data_dict)

            # Iterate over model fields to get metadata
            if hasattr(data_obj, "model_fields"):
                for field_name, field_info in data_obj.model_fields.items():
                    # Get json_schema_extra safely
                    extra = getattr(field_info, "json_schema_extra", None)
                    # Field name must exist in data
                    if field_name not in masked_data:
                        continue
                    value = masked_data[field_name]
                    # Check if extra metadata exists before accessing it
                    if extra is None:
                        continue
                    is_sensitive = extra.get("sensitive", False)
                    is_db_connection_url = extra.get(
                        "db_connection_url", False
                    )
                    if is_sensitive and is_db_connection_url:
                        # db_connection_url=True: mask password in URL
                        if isinstance(value, str) and "://" in value:
                            masked_data[field_name] = (
                                Library._mask_connection_url(value, mask_value)
                            )
                    # Check for sensitive marker
                    elif is_sensitive:
                        # sensitive=True: replace entire field with mask value
                        masked_data[field_name] = mask_value
            return masked_data
        except Exception:
            return {}

    @staticmethod
    def mask_password(
        configs,
        password_replace="*" * 8,
        keys_to_match=r"^(?:_.*|.*(password|secret|hidden|token|salt|.*connection_url).*)$",
    ):
        """Mask password and sensitive values.

        Args:
            configs: configs
            password_replace: password text to be replaced
            keys_to_match: keys to be matched (regular expression)

        Returns:
            replaced configs with masked sensitive values
        """
        configs = copy.deepcopy(configs)
        # if configs is dict
        if isinstance(configs, dict):
            new_config = {}
            for key, value in configs.items():
                # if key matches regex: keys_to_match
                regex = re.compile(keys_to_match, re.IGNORECASE)
                if regex.match(key):
                    # For connection URLs, mask the password in the URL string
                    if isinstance(value, str) and "://" in value:
                        new_config[key] = Library._mask_connection_url(
                            value, password_replace
                        )
                    else:
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
    def _mask_connection_url(url, mask_value="*" * 8):
        """Mask password in database connection URL.

        Args:
            url: Connection URL string
            mask_value: Value to replace password with

        Returns:
            URL string with masked password
        """
        # Pattern: scheme://user:password@host:port/db
        # Replace password between : and @
        pattern = r"(://[^:]+:)[^@]+(@)"
        return re.sub(pattern, f"\\1{mask_value}\\2", url)

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
        if uuid_str and uuid_str != "all":
            success, err_msgs = Library.validate_values_uuid(
                uuid_str, "instance_id"
            )
            if not success:
                return False, "\n".join(err_msgs), None

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
            if encode:
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
    def job_callback(job_id, job_status, backend, results, callbacks, user={}):
        """Job callback.

        Args:
            job_id: job id
            job_status: job status
            backend: backend
            results: job results
            callbacks: callbacks
            user: user related info
        """
        if not callbacks:
            return True
        project_id = None
        user_id = None
        if user:
            project_id = user.get("project_id", None)
            user_id = user.get("user_id", None)
        data = {
            "project_id": project_id,
            "user_id": user_id,
            "job_id": job_id,
            "job_status": job_status,
            "backend": backend,
            "results": results,
        }
        success, err_msg = Library.run_callbacks(data, callbacks)
        if not success:
            logger.error(f"Job: {job_id} callback error: {err_msg}")
        return success


def _s(secret):
    """Secret text wrapper.

    Args:
        secret: secret text to be wrapped

    Returns:
        wrapped secret text
    """
    return secret
