编译、安装和运行 (基于K8s pod)
===============================

本章节介绍容器化部署方式，通过编译成容器镜像完成K8s环境下QCOS的安装和运行，为可选部署方案。

.. contents:: 目录
   :local:
   :depth: 3

前提条件
------------
保证操作系统已安装了docker、docker-compose等组件

.. code-block:: shell

   # BCLinux/CentOS/OpenEuler环境下示例:
   yum install -y docker docker-compose rsync

.. include:: edit-env.rst

编译qcos容器镜像
--------------------
.. code-block:: shell

   # 操作系统镜像 (容器内包含命令行)
   ./build-images.sh

   # 独立的命令行镜像 [可选]
   ./build-sandbox.sh  # 编译qcos-cli wheel包用的容器环境
   ./run-sandbox.sh  # 运行sandbox容器环境
   ./build-images.sh --cli

修改配置文件
--------------------

创建和修改全局配置文件
****************************
参照代码库中etc/qcos/qcos.toml, 创建和修改全局配置文件/etc/qcos/qcos.toml
修改或添加DEVICE_LIST中的设备列表

**注意**: 如果不创建该文件, 容器模式下会自动创建

创建和修改设备配置文件
****************************
参照代码库中etc/qcos/conf.d/dummy.toml等, 创建和修改设备配置文件/etc/qcos/conf.d/dummy.toml等

**注意**: 设备配置文件必须位于/etc/qcos/conf.d下, 文件名需要和qcos.toml中DEVICE_LIST列出的设备名一致。
文件中section必须对应相关设备名, 比如dummy设备的配置需要放在section: [dummy]下

运行容器 (基于K8s pod)
--------------------------
.. code-block:: shell

   # 基于K8s pod运行:
   cd deploy-scripts/k8s
   # 创建配置文件, 设置环境变量
   cp ./k8s-env.template ./k8s-env
   # 修改k8s-env中的变量
   # 注意:
   # 1. 可用过配置不同的QCOS_NAMESPACE来启动多个操作系统实例
   vim ./k8s-env

   # 运行基于k8s的操作系统pod容器: qcos
   ./run-k8s-qcos.sh -e k8s-env
   # 运行基于k8s的命令行容器: qcos-cli
   ./run-k8s-qcos-cli.sh -e k8s-env

   # 删除K8s pod:
   ./delete-k8s-qcos.sh -e k8s-env
