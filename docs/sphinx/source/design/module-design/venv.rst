驱动软件包虚拟环境
========================

QCOS 的量子设备驱动（如 qutip_sim、spinq、quafu 等）各自依赖不同的
Python 软件包，且部分驱动依赖之间存在版本冲突。为避免依赖冲突并支持
多驱动并行运行，QCOS 为每个驱动创建独立的 Python 虚拟环境（venv），
Prefect worker 进程在各自隔离的 venv 中加载驱动模块。
在编译QCOS容器，会默认创建驱动软件包虚拟环境部署

.. contents:: 目录
   :local:
   :depth: 3

配置文件
------------------------------

驱动 venv 配置文件位于 ``requirements/venv-configs.toml``，每个驱动的
配置项包括：

* ``module_name``：驱动 Python 模块名
* ``deps_pyproject_file``：依赖来源的 ``pyproject.toml`` 文件路径
* ``deps_sections``：依赖分区名列表（对应 ``pyproject.toml`` 中
  ``[project.optional-dependencies]`` 下的分区）
* ``envs``：可用 Python 解释器列表（按优先级匹配）

安装部署
------------------------------

使用 ``requirements/install-venvs.py`` 脚本一键创建所有 venv：

.. code-block:: shell

    # 进入项目根目录
    $ cd /root/qcos-project

    # 安装所有配置的 venv（包括 default、sandbox 和各驱动 venv）
    $ python3 requirements/install-venvs.py

    # 仅安装特定驱动的 venv
    $ python3 requirements/install-venvs.py --name DriverQutipSim

    # 安装多个驱动的 venv（逗号分隔）
    $ python3 requirements/install-venvs.py --name DriverQutipSim,DriverQuafu

    # 查看帮助
    $ python3 requirements/install-venvs.py --help

venv 安装目录默认为 ``/var/lib/qcos/venv/<name>``，其中 ``<name>``
为 venv 配置项的 key（如 ``DriverQutipSim``、``DriverQuafu``）。

调试验证
------------------------------

在开发或调试驱动时，可以手动 source 对应的 venv 环境：

.. code-block:: shell

    # 进入 quafu 驱动的 venv 环境进行调试
    $ source /var/lib/qcos/venv/DriverQutipSim/bin/activate

    # 验证驱动模块可导入
    (DriverQutipSim) $ python3 -c "import qutip; print('OK')"

    # 退出 venv
    (DriverQutipSim) $ deactivate

修改依赖后重新安装
------------------------------

当驱动的依赖发生变化（如 ``pyproject.toml`` 中新增或修改了驱动依赖分区），
需要重新运行安装脚本更新 venv：

.. code-block:: shell

    # 重新安装所有 venv（会增量更新已存在的 venv）
    $ python3 requirements/install-venvs.py

    # 重新安装特定驱动的 venv
    $ python3 requirements/install-venvs.py --name DriverQutipSim
