版本升级和发布
===================

本章节介绍了版本升级发布操作方法。

.. contents:: 目录
   :local:
   :depth: 2

版本升级和发布的手动流程
---------------------------

版本升级和发布流程:

develop切release分支 → 修改并提交版本号 → 全量测试（单元/集成/回归）→ 修复测试问题（若有）→ 再次测试直到通过 → 清理工作目录 → 打annotated tag → 编译发布产物 → 推送 tag/分支 → 合并主线

详细步骤如下:

- 从develop切换出release/v1.0.1分支

  .. code-block:: shell

     git checkout develop
     git pull origin develop
     git checkout -b release/v1.0.1

- 对项目中多个配置文件中的版本号变量进行修改, 版本号需符合语义化版本(SemVer)规范。 可参考.bumpversion.cfg中的配置文件，找到需要修改的版本号变量和文件位置
- 更新CHANGELOG.md中的新版本变更日志信息
- 提交版本变量和日志变更信息的修改, 提交信息可以是: Bump version: v1.0.0 -> v1.0.1
- 进行发布前最后的测试

  .. code-block:: shell

     cicd/run-cicd.sh

- 确保当前git工作目录没有尚未提交的代码, 保证git仓库是clean状态
- 推送分支代码和tag标签, 并合并回master和develop分支

  - 先推送release分支和tag:

    .. code-block:: shell

       git push origin release/v1.0.1
       git push origin v1.0.1

  - 合并到master分支:

    .. code-block:: shell

       git checkout master
       git pull origin master
       git merge --no-ff release/v1.0.1

  - 合并后推送master分支:

    .. code-block:: shell

       git push origin master

  - 合并到develop分支:

    .. code-block:: shell

       git checkout develop
       git pull origin develop
       git merge --no-ff release/v1.0.1

  - 若有冲突，解决冲突后提交，再推送develop分支:

    .. code-block:: shell

       git push origin develop

- 编译并发布文档、wheel包、容器等 (也可通过CICD进行)

  .. code-block:: shell

     build-scripts/build-images.sh

版本升级和发布一键自动化命令
------------------------------

为了简化上述手动升级和发布步骤，可以使用下列命令一键完成版本升级和提交

.. code-block:: shell

    # 指定版本号名称
    ./cicd/release-version.py -n 1.0.1
    或者
    # 自动版本号, 需要指定是对major、minor、patch版本进行自动版本号+1升级
    ./cicd/release-version.py -p [major | minor | patch]

    # 完整示例 (社区)
    ./cicd/release-version.py -n 1.0.1

    # 完整示例 (内部)
    ./cicd/release-version.py -n 1.0.1 --master-branch master --develop-branch dev_gitee --release-branch release_BC-QSE_V1.0.1_20251219 --skip-push

注意: 建议在使用命令前先进行试运行, 加上试运行(``--dry-run``)参数

.. code-block:: shell

    # 试运行
    ./cicd/release-version.py --dry-run -n 1.0.1
