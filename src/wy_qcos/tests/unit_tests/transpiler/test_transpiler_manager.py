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

from unittest.mock import patch, MagicMock
import pytest

from wy_qcos.common.library import Library
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.transpiler.transpiler_manager import TranspilerManager


class TestTranspilerManager:
    """Test suite for TranspilerManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh TranspilerManager instance for each test."""
        return TranspilerManager()

    @patch.object(Library, "find_dirs")
    @patch.object(Library, "import_classes")
    def test_load_transpilers(
        self, mock_import_classes, mock_find_dirs, manager
    ):
        """Test loading transpilers from directories."""
        # Arrange
        mock_find_dirs.return_value = ["/fake/dir"]

        mock_transpiler_instance = MagicMock()
        mock_transpiler_instance.enable = True
        mock_transpiler_instance.get_name.return_value = "cmss"
        mock_transpiler_instance.set_module_name = MagicMock()
        mock_transpiler_instance.set_class_name = MagicMock()

        mock_transpiler_class = MagicMock(
            return_value=mock_transpiler_instance
        )
        mock_transpiler_class.__module__ = (
            "wy_qcos.transpiler.cmss.transpiler_cmss"
        )
        mock_transpiler_class.__qualname__ = "TranspilerCmss"

        classes = {"TranspilerCmss": mock_transpiler_class}
        mock_import_classes.return_value = classes, {}

        # Act
        manager.load_transpilers()

        # Assert
        mock_find_dirs.assert_called_once()
        mock_import_classes.assert_called_once()
        assert mock_import_classes.call_args[1]["base_class"] == TranspilerBase
        assert mock_import_classes.call_args[1]["excluded_class"] == "Base$"
        assert manager.has_transpiler("cmss")
        assert manager.get_transpiler("cmss") is mock_transpiler_instance

    @patch.object(Library, "find_dirs")
    @patch.object(Library, "import_classes")
    def test_init_transpilers(
        self, mock_import_classes, mock_find_dirs, manager
    ):
        """Test initializing loaded transpilers."""
        # Arrange
        mock_find_dirs.return_value = ["/fake/dir"]
        mock_transpiler_instance = MagicMock()
        mock_transpiler_instance.enable = True
        mock_transpiler_instance.get_name.return_value = "test_transpiler"
        mock_transpiler_instance.init_transpiler = MagicMock()
        mock_transpiler_instance.get_transpiler_info = MagicMock(
            return_value="Test Transpiler Info"
        )

        mock_transpiler_class = MagicMock(
            return_value=mock_transpiler_instance
        )
        mock_transpiler_class.__module__ = "test.module"
        mock_transpiler_class.__qualname__ = "TestTranspiler"

        classes = {"TestTranspiler": mock_transpiler_class}
        mock_import_classes.return_value = classes, {}

        # Act
        manager.load_transpilers()
        manager.init_transpilers()

        # Assert
        mock_transpiler_instance.init_transpiler.assert_called_once()
        mock_transpiler_instance.get_transpiler_info.assert_called_once()

    def test_has_transpiler_true(self, manager):
        """Test has_transpiler returns True for existing transpiler."""
        # Arrange
        mock_transpiler = MagicMock()
        manager.transpilers["existing_transpiler"] = mock_transpiler

        # Act
        result = manager.has_transpiler("existing_transpiler")

        # Assert
        assert result is True

    def test_has_transpiler_false(self, manager):
        """Test has_transpiler returns False for non-existing transpiler."""
        # Act
        result = manager.has_transpiler("non_existing_transpiler")

        # Assert
        assert result is False

    def test_get_transpiler_found(self, manager):
        """Test get_transpiler returns transpiler instance."""
        # Arrange
        mock_transpiler = MagicMock()
        manager.transpilers["test_transpiler"] = mock_transpiler

        # Act
        result = manager.get_transpiler("test_transpiler")

        # Assert
        assert result is mock_transpiler

    def test_get_transpiler_not_found(self, manager):
        """Test get_transpiler returns None for non-existing transpiler."""
        # Act
        result = manager.get_transpiler("non_existing_transpiler")

        # Assert
        assert result is None

    def test_get_transpilers_empty(self, manager):
        """Test get_transpilers returns empty dict when no transpilers."""
        # Act
        transpilers = manager.get_transpilers()

        # Assert
        assert isinstance(transpilers, dict)
        assert len(transpilers) == 0

    def test_get_transpilers_with_multiple(self, manager):
        """Test get_transpilers returns all loaded transpilers."""
        # Arrange
        mock_transpiler1 = MagicMock()
        mock_transpiler2 = MagicMock()
        manager.transpilers["transpiler1"] = mock_transpiler1
        manager.transpilers["transpiler2"] = mock_transpiler2

        # Act
        transpilers = manager.get_transpilers()

        # Assert
        assert len(transpilers) == 2
        assert transpilers["transpiler1"] is mock_transpiler1
        assert transpilers["transpiler2"] is mock_transpiler2

    @patch.object(Library, "find_dirs")
    @patch.object(Library, "import_classes")
    def test_load_transpilers_disabled_transpiler(
        self, mock_import_classes, mock_find_dirs, manager
    ):
        """Test loading skips disabled transpilers."""
        # Arrange
        mock_find_dirs.return_value = ["/fake/dir"]

        mock_transpiler_instance = MagicMock()
        mock_transpiler_instance.enable = False

        mock_transpiler_class = MagicMock(
            return_value=mock_transpiler_instance
        )
        mock_transpiler_class.__module__ = "test.module"
        mock_transpiler_class.__qualname__ = "DisabledTranspiler"

        classes = {"DisabledTranspiler": mock_transpiler_class}
        mock_import_classes.return_value = classes, {}

        # Act
        manager.load_transpilers()

        # Assert
        assert len(manager.transpilers) == 0

    @patch.object(Library, "find_dirs")
    @patch.object(Library, "import_classes")
    def test_load_transpilers_multiple_directories(
        self, mock_import_classes, mock_find_dirs, manager
    ):
        """Test loading transpilers from multiple directories."""
        # Arrange
        mock_find_dirs.return_value = ["/dir1", "/dir2"]

        mock_transpiler_instance1 = MagicMock()
        mock_transpiler_instance1.enable = True
        mock_transpiler_instance1.get_name.return_value = "transpiler1"
        mock_transpiler_instance1.set_module_name = MagicMock()
        mock_transpiler_instance1.set_class_name = MagicMock()

        mock_transpiler_instance2 = MagicMock()
        mock_transpiler_instance2.enable = True
        mock_transpiler_instance2.get_name.return_value = "transpiler2"
        mock_transpiler_instance2.set_module_name = MagicMock()
        mock_transpiler_instance2.set_class_name = MagicMock()

        mock_class1 = MagicMock(return_value=mock_transpiler_instance1)
        mock_class1.__module__ = "module1"
        mock_class1.__qualname__ = "Class1"

        mock_class2 = MagicMock(return_value=mock_transpiler_instance2)
        mock_class2.__module__ = "module2"
        mock_class2.__qualname__ = "Class2"

        classes1 = {"Class1": mock_class1}
        classes2 = {"Class2": mock_class2}
        mock_import_classes.side_effect = [
            (classes1, {}),
            (classes2, {}),
        ]

        # Act
        manager.load_transpilers()

        # Assert
        assert mock_find_dirs.call_count == 1
        assert mock_import_classes.call_count == 2
        assert manager.has_transpiler("transpiler1")
        assert manager.has_transpiler("transpiler2")
