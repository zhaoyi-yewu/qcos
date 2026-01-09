版本软件包发布
===================

本章节介绍了版本软件包发布操作方法。

.. contents:: 目录
   :local:
   :depth: 2

版本软件包发布的手动流程
---------------------------

版本软件包发布流程:

软件包(包括: wheel包、源代码)发布到PYPI上 → 文档制品(html、pdf)发布到ReadTheDocs上(可自动执行) →
容器镜像发布到dockerhub上
可以配置流水线进行上述发布，也可以通过下面的一键部署脚本进行发布

版本软件包发布一键自动化命令
------------------------------

为了简化上述手动发布步骤，可以使用下列命令一键完成版本发布

.. code-block:: shell

    # 发布软件包
    ./cicd/publish.py packages
    # 发布容器镜像
    ./cicd/publish.py images

注意: 建议在使用命令前先进行试运行, 加上试运行(``--dry-run``)参数

.. code-block:: shell

    # 试运行
    # 发布软件包
    ./cicd/publish.py packages --dry-run
    # 发布容器镜像
    ./cicd/publish.py images ---dry-run
