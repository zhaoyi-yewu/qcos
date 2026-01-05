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
     yum install -y python3 python3-pip python3-sphinx python3-requests

- 安装Python依赖包：

  .. code-block:: shell

     pip3 install -r ./requirements/requirements.txt -r ./requirements/requirements-test.txt

编辑.env配置文件
--------------------
进入编译脚本目录，复制配置模板并编辑.env文件：

.. code-block:: shell

   cd build-scripts
   cp ./env.template .env
   vim .env
   # .env配置文件说明
   # 1. DEV选项为False时表示编译出的镜像是生产环境镜像; True时表示编译出来的是开发环境镜像。开发环境会挂载(mount)宿主机源代码到容器中, 直接使用挂载的源代码运行, 方便开发者在宿主机上修改代码。而生产环境镜像中会集成源代码。
   # 2. 需要填写PREFECT_SERVER_API_HOST地址(一般填写为本机IP地址或者127.0.0.1)
   # 3. 如果本地可以访问外网, 无需填写YUM_MIRROR, PIP_MIRROR
   # 4. 如果本地无法访问外网, 需要保证局域网内有OpenEuler操作系统的YUM镜像源(YUM_MIRROR), 以及Python软件包镜像源(PIP_MIRROR)。
   # YUM_MIRROR地址格式示例: http://mirrors.cmecloud.cn
   # PIP_MIRROR地址格式示例: http://mirrors.cmecloud.cn/pip/simple
   # 5. DEBUG是内部开发使用的调试开关, 可以配成默认的False
   # 6. LOCAL_CICD是本地CICD的标记开关, 可以配成默认的False
   # 7. REGISTRY为Docker容器私有镜像仓库地址, 如果本机可以访问DockerHub, 则可以留空

编译安装
------------

基于poetry编译操作系统wheel包
************************************
在build-scripts目录下执行编译脚本或直接使用poetry构建：

.. code-block:: shell

   # BCLinux/CentOS/OpenEuler环境下示例:
   cd build-scripts
   ./build-wheel.sh
   # 或直接使用poetry命令
   poetry build

安装wheel包
******************
执行pip3命令安装编译好的wheel包，并配置服务运行所需的目录和环境变量：

.. code-block:: shell

   # 安装wheel包
   pip3 install --prefix=/usr ./output/dist/qcos-1.0.0-py3-none-any.whl

   # 创建服务运行所需目录
   mkdir -p /var/qcos/db/; mkdir -p /var/qcos/storage

   # 设置系统环境变量（临时生效，如需永久生效请写入/etc/profile或~/.bashrc）
   export PREFECT_SERVER_API_HOST="127.0.0.1"
   export PREFECT_SERVER_DATABASE_CONNECTION_URL="sqlite+aiosqlite:////var/qcos/db/prefect.db"
   export PREFECT_API_URL="http://127.0.0.1:4200/api"
   export PREFECT_LOCAL_STORAGE_PATH="/var/qcos/storage"
   export PREFECT_API_DEFAULT_LIMIT=100000

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

**注意**: 设备配置文件必须位于/etc/qcos/conf.d下, 文件名需要和qcos.toml中DEVICE_LIST列出的设备名一致。 文件中section必须对应相关设备名, 比如dummy设备的配置需要放在section: [dummy]下

运行服务
------------
依次启动Prefect服务和QCOS服务：

.. code-block:: shell

   # 启动Prefect Server服务
   prefect server start

   # 启动QCOS API服务（指定配置文件和配置目录）
   qcos-api --config-file /etc/qcos/qcos.toml --config-dir /etc/qcos/conf.d/
