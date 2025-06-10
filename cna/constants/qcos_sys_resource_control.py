#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-07
# ------------------------


from enum import Enum, auto

# 定义权限类，假设它是一个枚举或类
class Permission(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    OPERATE = auto()


# 定义进程状态枚举
class ProcessState(Enum):
    CREATED = auto()
    RUNNING = auto()
    WAITING = auto()
    TERMINATED = auto()


# 定义资源类型枚举
class ResourceType(Enum):
    FILE = auto()
    DEVICE = auto()
    QUBIT = auto()
