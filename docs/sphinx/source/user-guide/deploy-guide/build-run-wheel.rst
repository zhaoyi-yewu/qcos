编译、安装和运行 (基于wheel)
=============================

本章节介绍非容器化部署方式，通过编译wheel包完成QCOS的安装和运行，为可选部署方案。

.. contents:: 目录
   :local:
   :depth: 3

前提条件
------------
需确保操作系统已安装Python 3及相关组件，具体步骤如下：

- 安装系统级Python组件：

  .. code-block:: shell

     # BCLinux/CentOS/OpenEuler环境下示例:
     # 需保证Python3>=3.11版本
     # cmake/gcc-c++/make/boost-devel/gtest-devel 用于编译 C++ 扩展(high_performance.so)
     yum install -y python3 python3-pip python3-sphinx python3-requests python3-alembic gcc gcc-c++ make cmake boost-devel gtest-devel python3-devel
     pip3 install tomlkit poetry

- 安装Python依赖包：

  .. code-block:: shell

     使用venv虚拟隔离环境 (可避免各驱动软件包的冲突问题)
     cd ./requirements
     ./install-venvs.py

     注意: 如果要从pyproject.toml中导出requirements-[模块].txt, 可以执行下列命令，导出的文件位于当前的./requirements目录下
     ./install-venvs.py --export-requirements

.. include:: edit-env.rst

编译安装QCOS软件包
--------------------

基于poetry编译操作系统QCOS wheel包
************************************
在build-scripts目录下执行编译脚本或直接使用poetry构建：

.. code-block:: shell

   # BCLinux/CentOS/OpenEuler环境下示例:
   cd build-scripts
   ./build-wheel.sh
   # 或直接使用poetry命令
   poetry build

安装QCOS wheel包
******************
执行pip3命令安装编译好的wheel包，并配置服务运行所需的目录和环境变量：

.. code-block:: shell

   # 安装wheel包
   cd build-scripts
   pip3 install --prefix=/usr ./output/dist/wy_qcos-1.5.0-cp311-cp311-linux_x86_64.whl

   # 创建服务运行所需目录
   mkdir -p /var/qcos/db/; mkdir -p /var/qcos/storage

   # 设置系统环境变量（临时生效，如需永久生效请写入/etc/profile或~/.bashrc）
   export PREFECT_SERVER_API_HOST="127.0.0.1"
   export PREFECT_SERVER_DATABASE_CONNECTION_URL="postgresql+asyncpg://qcos:${password}@127.0.0.1:5432/qcos"
   export PREFECT_API_URL="http://127.0.0.1:4200/api"
   export PREFECT_LOCAL_STORAGE_PATH="/var/qcos/storage"
   export PREFECT_API_DEFAULT_LIMIT=100000

编译安装QCOS Client命令行软件包
--------------------------------

基于poetry编译操作系统QCOS Client wheel包
******************************************
在build-scripts/cli目录下执行编译脚本或直接使用poetry构建：

.. code-block:: shell

   # BCLinux/CentOS/OpenEuler环境下示例:
   cd build-scripts/cli
   ./build-wheel.sh
   # 或直接使用poetry命令
   poetry build

安装QCOS Client wheel包
****************************
执行pip3命令安装编译好的wheel包，并配置服务运行所需的目录和环境变量：

.. code-block:: shell

   # 安装wheel包
   cd build-scripts/cli
   pip3 install --prefix=/usr ./output/dist/wy_qcos_client-1.5.0-py3-none-any.whl

修改配置文件
----------------

创建和修改全局配置文件
****************************
参照代码库中etc/qcos/qcos.toml, 创建和修改全局配置文件/etc/qcos/qcos.toml
修改或添加DEVICE_LIST中的设备列表

**注意**: 如果不创建该文件, 容器模式下会自动创建

创建和修改设备配置文件
****************************
参照代码库中etc/qcos/conf.d/dummy.toml等, 创建和修改设备配置文件/etc/qcos/conf.d/dummy.toml等

**注意**: 设备配置文件必须位于/etc/qcos/conf.d下, 文件名需要和qcos.toml中
DEVICE_LIST列出的设备名一致。 文件中section必须对应相关设备名, 比如dummy设备的配置需要放在section: [dummy]下

运行QCOS服务
------------
依次启动Prefect服务和QCOS服务：

.. code-block:: shell

   # 创建Prefect Server数据库和账户（只对后端数据库为postgres数据库, 仅首次运行或需要重置数据库时执行）
   psql -U postgres -c "CREATE USER prefect WITH PASSWORD '{PREFECT数据库账户密码}' INHERIT;"
   psql -U postgres -c "CREATE DATABASE prefect WITH OWNER prefect;"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE prefect TO $prefect;"
   psql -U postgres -d prefect -c "ALTER SCHEMA public OWNER TO prefect;"
   psql -U postgres -d prefect -c "GRANT ALL PRIVILEGES ON SCHEMA public TO prefect;"
   psql -U postgres -d prefect -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO prefect;"
   psql -U postgres -d prefect -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO prefect;"
   psql -U postgres -d prefect -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO prefect;"
   psql -U postgres -d prefect -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO prefect;"

   # 初始化QCOS数据库和账户（只对后端数据库为postgres数据库, 仅首次运行或需要重置数据库时执行）
   psql -U postgres -c "CREATE USER qcos WITH PASSWORD '{QCOS数据库账户密码}' INHERIT;"
   psql -U postgres -c "CREATE DATABASE qcos WITH OWNER qcos;"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE qcos TO qcos;"
   psql -U postgres -d qcos -c "ALTER SCHEMA public OWNER TO qcos;"
   psql -U postgres -d qcos -c "GRANT ALL PRIVILEGES ON SCHEMA public TO qcos;"
   psql -U postgres -d qcos -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO qcos;"
   psql -U postgres -d qcos -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO qcos;"
   psql -U postgres -d qcos -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO qcos;"
   psql -U postgres -d qcos -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO qcos;"

   # 启动Prefect Server服务
   prefect server start

   # 启动redis服务
   systemctl start redis 或者 redis-server

   # 启动postgresql服务
   systemctl start postgresql 或者 pg_ctl -D /var/lib/pgsql/data start

   # 运行db-manager.sh脚本初始化、迁移和升级数据库表结构
   cd build-scripts
   ./db-manager.sh -i -u

   # 启动QCOS API服务（指定配置文件和配置目录）
   qcos-api --config-file /etc/qcos/qcos.toml --config-dir /etc/qcos/conf.d/
