开发调试问题
==============

本章节介绍了开发调试问题和技巧等问题。

.. contents:: 目录
   :local:
   :depth: 3


如何通过DEBUG日志进行调试？
--------------------------------

开发环境下开启DEBUG=True（在.env文件中配置或者/etc/qcos/qcos.toml中），获取详细报错栈
在代码中添加logger.debug()打印关键变量：

.. code-block:: python

    import logging

    logger = logging.getLogger(__name__)

    def run(self, code):
        logger.debug(f"执行量子代码：{code}")

如何通过代码断点进行调试？
--------------------------------

在代码中需要断点的地方，添加pdb或者打印

.. code-block:: python

    type = 1
    print(f"test: {type}")
    import pdb;pdb.set_trace()
    pass
