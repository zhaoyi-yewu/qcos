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

代码/文档一键自动化检查
------------------------

代码/文档一键自动化检查脚本

.. code-block:: shell

   # 在qcos-sandbox容器内执行以下命令：
   ./cicd/run-cicd.sh



代码问题单项检查
------------------------

如果不使用代码/文档一键自动化检查脚本, 也可以逐个单项进行检查
在qcos-sandbox容器内执行以下命令：

代码格式检查
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   ./cicd/code-formatter.sh

注意 如果格式检查失败，可以手动改代码修复格式问题，也可以通过下列命令尝试自动修复：

.. code-block:: shell

   ./cicd/code-formatter.sh -f


代码静态检查
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   ./cicd/code-linter.sh

注意 如果代码静态检查失败，可以手动改代码修复问题，也可以通过下列命令尝试自动修复：

.. code-block:: shell

   ./cicd/code-linter.sh -f

代码docstring检查
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   ./cicd/docstring-check.sh

文档代码(markdown/rst)静态检查
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   ./cicd/docs-linter.sh

注意 如果文档代码静态检查失败，可以手动改代码修复问题，也可以通过下列命令尝试自动修复：

.. code-block:: shell

   ./cicd/docs-linter.sh -f

执行单元测试(UT)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 1. QCOS单元测试
   ./cicd/run-tests.sh -u all

   # 2. QCOS CLIENT单元测试
   ./cicd/run-tests.sh -j all

执行覆盖率测试(Coverage)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

确保代码覆盖率不低于：80%

.. code-block:: shell

   # 1. QCOS代码覆盖率测试
   ./cicd/run-tests.sh -c all

   # 2. QCOS CLIENT代码覆盖率测试
   ./cicd/run-tests.sh -e all

   # 在qcos-sandbox容器内可通过以下方式查看覆盖率报告：
   # 方式1：使用浏览器打开HTML报告（需容器内有浏览器或映射端口到宿主机）
   # 浏览器访问 ./coverage_html/index.html

   # 方式2：命令行模式查看简洁报告（可选）
   coverage3 report -m

   # 方式3：命令行通过links工具查看HTML报告（可选，需安装links）
   links ./coverage_html/index.html

执行系统测试(ST) [可选]
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 1. 配置测试参数（修改被测服务的IP和端口）
   vi /etc/qcos/qcos-st.toml  # 调整API_SERVER_IP和API_SERVER_PORT为实际值

   # 2. 运行系统测试
   cd ./cicd
   ./run-tests.sh -s all
