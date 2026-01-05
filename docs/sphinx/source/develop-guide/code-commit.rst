代码开发协作和要求
===================

本章节介绍了代码开发协作和要求。

.. contents:: 目录
   :local:
   :depth: 3

分支管理策略
---------------------------

功能开发：从develop分支同步到个人本地分支，完成后提MR/PR到develop


代码评审要求
---------------------------

MR/PR须填写 “功能说明”
至少1名核心开发者审批通过才能合并

代码提交前自检清单
---------------------------

代码提交前，务必在本地先进行下列检查，保证代码符合项目规范

代码/文档一键自动化检查
****************************

代码/文档一键自动化检查脚本

.. code-block:: shell

    ./cicd/run-cicd.sh

代码问题单项检查
****************************

如果不使用代码/文档一键自动化检查脚本, 也可以逐个单项进行检查

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

    ./cicd/run-tests.sh -u

执行覆盖率测试(Coverage)，确保覆盖率不低于：80%
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

    ./cicd/run-tests.sh -c

执行系统测试(ST) [可选]
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

    ./cicd/run-tests.sh -s
