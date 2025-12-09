编译、安装和运行 (推荐, 基于Docker容器)
=======================================

本章节介绍容器化部署方式，通过编译成容器镜像完成Docker环境下QCOS的安装和运行，为推荐部署方案。

.. contents:: 目录
   :local:
   :depth: 3

前提条件
-----------------
保证操作系统已安装了docker、docker-compose等组件

.. code-block:: shell

   # BCLinux/CentOS/OpenEuler环境下示例:
   yum install -y docker docker-compose rsync

编辑.env配置文件
-----------------
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

编译qcos容器镜像
-----------------
.. code-block:: shell

   # 操作系统镜像 (容器内包含命令行)
   ./build-images.sh

   # 独立的命令行镜像 [可选]
   ./build-sandbox.sh  # 编译qcos-cli wheel包用的容器环境
   ./run-sandbox.sh  # 运行sandbox容器环境
   ./build-images.sh --cli

修改配置文件
-----------------

创建和修改全局配置文件
***************************
参照代码库中etc/qcos/qcos.toml, 创建和修改全局配置文件/etc/qcos/qcos.toml  
修改或添加DEVICE_LIST中的设备列表  

**注意**: 如果不创建该文件, 容器模式下会自动创建

创建和修改设备配置文件
***************************
参照代码库中etc/qcos/conf.d/dummy.toml等, 创建和修改设备配置文件/etc/qcos/conf.d/dummy.toml等  

**注意**: 设备配置文件必须位于/etc/qcos/conf.d下, 文件名需要和qcos.toml中DEVICE_LIST列出的设备名一致。 文件中section必须对应相关设备名, 比如dummy设备的配置需要放在section: [dummy]下

运行容器 (基于Docker)
---------------------------
.. code-block:: shell

   # 基于docker容器运行
   cd build-scripts
   ./run-docker.sh
