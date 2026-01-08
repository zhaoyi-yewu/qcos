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

from wy_qcos.transpiler.common.errors import MappingException
from wy_qcos.transpiler.cmss.mapping.routing.mcts_routing import MCTSRouting
from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing_wrapper import (
    SABRERouting,
)


class SCRoutingFactory:
    """超导设备路由算法工厂类.

    根据参数选择具体的路由算法实现（MCTS或SABRE）。
    """

    @staticmethod
    def create_routing(routing_algorithm: str = "mct", **kwargs):
        """创建路由算法实例.

        Args:
            routing_algorithm: 路由算法名称，支持 "mct", "sc", "sabre"
            **kwargs: 路由算法的额外参数
                - 对于SABRE算法：extention_size, weight, decay
                - 对于MCTS算法：selec_times

        Returns:
            路由算法实例（MCTSRouting 或 SABRERouting）

        Raises:
            MappingException: 如果路由算法名称不支持
        """
        if routing_algorithm in ("mct", "sc"):
            # 使用蒙特卡罗树搜索算法（默认）
            routing = MCTSRouting()
            # 如果提供了selec_times参数，设置它
            if "selec_times" in kwargs:
                routing.selec_times = kwargs["selec_times"]
            return routing
        elif routing_algorithm == "sabre":
            # 使用SABRE算法
            extention_size = kwargs.get("extention_size", 20)
            weight = kwargs.get("weight", 0.5)
            decay = kwargs.get("decay", 0.001)
            return SABRERouting(
                extention_size=extention_size,
                weight=weight,
                decay=decay,
            )
        else:
            raise MappingException(
                f"Unsupported routing algorithm: {routing_algorithm}. "
                f"Supported algorithms: 'mct', 'sc', 'sabre'"
            )


# 为了向后兼容，保留 SCRouting 作为 MCTSRouting 的别名
SCRouting: type[MCTSRouting] = MCTSRouting
