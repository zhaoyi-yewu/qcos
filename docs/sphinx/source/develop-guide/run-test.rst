测试和CICD
===================

本章节介绍QCOS的各类测试执行方式，包括单元测试、覆盖率测试、系统测试及代码格式与静态分析，推荐在容器环境中运行测试，也可和CICD集成。

.. contents:: 目录
   :local:
   :depth: 3

通过容器环境运行测试
------------------------
首先启动并进入qcos-sandbox容器环境：

.. code-block:: shell

   ./run-sandbox.sh
   docker exec -it qcos-sandbox bash

单元测试 (UT)
------------------------
在qcos-sandbox容器内执行以下命令运行单元测试：

.. code-block:: shell

   cd ./cicd
   ./run-tests.sh -u

覆盖率测试 (Coverage)
------------------------
在qcos-sandbox容器内执行以下命令运行覆盖率测试：

.. code-block:: shell

   cd ./cicd
   ./run-tests.sh -c

覆盖率报告查看
*********************
在qcos-sandbox容器内可通过以下方式查看覆盖率报告：

.. code-block:: shell

   cd ./cicd
   # 方式1：使用浏览器打开HTML报告（需容器内有浏览器或映射端口到宿主机）
   # 浏览器访问 ./coverage_html/index.html

   # 方式2：命令行模式查看简洁报告（可选）
   coverage3 report -m

   # 方式3：命令行通过links工具查看HTML报告（可选，需安装links）
   links ./coverage_html/index.html

系统测试 (ST)
--------------------
在qcos-sandbox容器内执行系统测试前，需确保QCOS服务已正常启动，并配置测试参数：

.. code-block:: shell

   # 1. 配置测试参数（修改被测服务的IP和端口）
   vi /etc/qcos/qcos-st.toml  # 调整API_SERVER_IP和API_SERVER_PORT为实际值

   # 2. 运行系统测试
   cd ./cicd
   ./run-tests.sh -s

代码格式检查 (ruff format)
---------------------------------
在qcos-sandbox容器内执行代码格式检查：

.. code-block:: shell

   # 方式1：直接使用ruff命令检查
   cd /path/to/project/root  # 进入项目根目录
   ruff format --preview --check --diff qcos

   # 方式2：使用脚本检查
   ./cicd/code-formatter.sh

   # 自动修复代码格式问题（可选）
   # 方式1：直接使用ruff命令修复
   ruff format --preview qcos

   # 方式2：使用脚本修复
   ./cicd/code-formatter.sh -f

代码静态分析lint (pylint+ruff+mypy)
-----------------------------------------
在qcos-sandbox容器内执行代码静态分析：

.. code-block:: shell

   # 方式1：分别执行各工具命令
   cd /root/qcos-project  # 进入项目根目录
   # pylint qcos  # 可选
   ruff check --preview qcos
   mypy qcos

   # 方式2：使用脚本执行所有静态分析
   ./cicd/code-linter.sh
