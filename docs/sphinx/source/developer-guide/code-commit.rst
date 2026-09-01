代码开发流程
==========================

本章节介绍了 QCOS 项目的代码开发流程、协作规范和提交要求。

.. contents:: 目录
   :local:
   :depth: 3


提交 Issue
------------------------------

在开始开发前，请先在Gitee的WUYUEQbit QCOS官方仓库网页上创建一个 Issue，说明本次提交的类型：

* **需求**：用于跟踪未来希望实现的新功能，本次暂不提交代码，仅提出需求
* **任务**：对应一个新功能（new feature），需要通过提交新代码来实现
* **缺陷**：对应一个新缺陷（bug），需要通过提交 bugfix 代码来修复

填写标题（简短概括）和内容（尽量详细描述），然后点击创建。

.. figure:: ../_static/developer-guide/create-new-issue1.png
   :alt: 新建 Issue 步骤一
   :width: 80%
   :align: center

   新建 Issue 步骤一

.. figure:: ../_static/developer-guide/create-new-issue2.png
   :alt: 新建 Issue 步骤二
   :width: 80%
   :align: center

   新建 Issue 步骤二


同步 Fork 的代码
------------------------------

在开发者自己 Fork 的代码仓库名称旁边，点击更新按钮同步代码，保证代码与上游仓库一致。

.. note::

    每次提交代码前，均需保证开发者侧的代码是最新的，否则可能会导致代码冲突或无法合并。

.. figure:: ../_static/developer-guide/fetch-code1.png
   :alt: 同步 QCOS 代码 步骤一
   :width: 80%
   :align: center

   同步 QCOS 代码 步骤一

.. figure:: ../_static/developer-guide/fetch-code2.png
   :alt: 同步 QCOS 代码 步骤二
   :width: 80%
   :align: center

   同步 QCOS 代码 步骤二


代码开发和提交
------------------------------

新功能开发（new feature）或修复问题（bug fix）的流程如下：

.. code-block:: shell

    # 切换到 develop 分支并拉取最新代码
    $ git checkout develop
    $ git pull --rebase

    # 创建新功能分支（格式: feature_新功能缩写，或使用 Gitee Issue ID: feature_IKC5TD）
    $ git branch -m feature_new_author
    或者
    $ git branch -m feature_IKC5TD

    # 或者创建问题修复分支（格式: bugfix_问题缩写，或使用 Gitee Issue ID: bugfix_IKC5TD）
    $ git branch -m bugfix_new_author
    或者
    $ git branch -m bugfix_IKC5TD

.. note::

    具体项目开发规范，参考： :doc:`项目开发规范 <developer-guidelines>`，
    也可参考和套用 AI Skill： :download:`SKILL.md <../../../../.roo/skills/develop-new-module/SKILL.md>`

修改代码：

.. code-block:: shell

    $ vim ./AUTHORS

.. figure:: ../_static/developer-guide/demo-add-author.png
   :alt: 开发示例：文件修改
   :width: 80%
   :align: center

   代码开发示例：文件修改

提交代码：

.. code-block:: shell

    $ git add AUTHORS
    $ git commit

添加提交信息时，要求如下格式：

1. **第一行**：本次提交的摘要（summary）
2. **空一行**
3. **第三行起**：Description 段落，按照 1、2、3 分点描述本次提交的主要修改内容

.. figure:: ../_static/developer-guide/demo-add-commit-messages.png
   :alt: 开发示例：添加 commit 信息
   :width: 80%
   :align: center

   代码开发示例：添加 commit 信息


代码提交前自检
------------------------------

代码提交前，务必在本地先执行自动化检查脚本，保证代码符合项目规范。

.. code-block:: shell

    # 在 qcos-sandbox 容器内执行以下命令
    ./cicd/run-cicd.sh

.. note::

    具体测试执行细节、测试种类等内容，可以参考： :doc:`测试和 CI/CD <run-tests>`


代码推送流程示例
------------------------------

推送代码提交到远程仓库：

.. code-block:: shell

    $ git push origin feature_new_author

推送成功后，gitee页面上会多出刚才推送的分支：feature_new_author，以及提交信息

.. figure:: ../_static/developer-guide/push-commit.png
   :alt: 成功推送代码
   :width: 80%
   :align: center

   成功推送代码

在 Gitee 上点击 **Pull Requests (PR)** 并创建：

.. figure:: ../_static/developer-guide/create-pull-request1.png
   :alt: 创建 Pull Request
   :width: 80%
   :align: center

   创建 Pull Request

填写 Pull Request 信息，包括：

* **源分支**：开发者刚刚提交的代码仓库和分支名
* **目标分支**：QCOS 官方仓库 ``WUYUEQbit/qcos``，分支 ``develop``
* **PR 标题**：简要描述本次变更
* **PR 描述**：分点描述变更内容
* **关联 Issue**：关联对应的 Gitee Issue
* **合并选项**：勾选"合并后删除提交分支"和"合并后关闭提到的 Issue"

.. figure:: ../_static/developer-guide/create-pull-request2.png
   :alt: 填写 Pull Request 详细信息
   :width: 80%
   :align: center

   填写 Pull Request 详细信息


代码评审
------------------------------

提交 PR 后，社区 CICD 自动化测试脚本和评审人员会对代码进行评审。
至少 **1 名核心开发者** 审批通过后才能合并。

如果评审时发现问题，可以在 Pull Request 中进行代码评审，添加评审意见：

.. figure:: ../_static/developer-guide/code-review1.png
   :alt: 添加 Code Review 评审意见
   :width: 80%
   :align: center

   添加 Code Review 评审意见

.. figure:: ../_static/developer-guide/code-review2.png
   :alt: 填写 Code Review 评审意见
   :width: 80%
   :align: center

   填写 Code Review 评审意见

.. figure:: ../_static/developer-guide/code-review3.png
   :alt: 提交 Code Review 评审意见
   :width: 80%
   :align: center

   提交 Code Review 评审意见

开发者查看 Gitee 上的 PR，当有人提出评审建议时，如果有争议或需要讨论，可以在下方评论区发表评论：

.. figure:: ../_static/developer-guide/code-review4.png
   :alt: 对 Code Review 意见进行讨论
   :width: 80%
   :align: center

   对 Code Review 意见进行讨论

如果没有争议，则重新修改代码后，强制推送更新，并把评论区意见置为 **已解决** 状态：

.. code-block:: shell

    $ vim AUTHORS
    $ git add AUTHORS
    $ git commit --amend --no-edit
    $ git push -f origin feature_new_author


代码合入
------------------------------

经 Code Review 后，社区 CICD 测试脚本和评审人员对代码评审均无问题后，
核心开发者将在 Gitee 上手动合并代码，代码合入成功。
开发者可在本地通过 ``git pull --rebase`` 更新最新代码
