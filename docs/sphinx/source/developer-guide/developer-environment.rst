开发环境搭建
===================

本章节介绍了开发环境搭建。

.. contents:: 目录
   :local:
   :depth: 3

环境要求清单
---------------------------

- 开发环境操作系统（如: BCLinux for Euler 21.10、OpenEuler 21/22/23/24、CentOS 7.9等主流Linux操作系统）
- 硬件最低配置 (4 核 CPU/8G 内存 / 50G 磁盘，开发环境建议配置)
- 网络权限 (是否需要访问内网镜像源、Git仓库地址)

软件要求清单
---------------------------

- 软件: Git、Docker/Docker Compose等
- Python 3.11+
- 推荐Python IDE及插件 (PyCharm或者VS Code等)

gitee网站上申请账户
---------------------------

https://gitee.com

Fork QCOS代码仓库
---------------------------

使用自己的gitee账户登陆，进入下列QCOS项目网址，并按右上角的Fork按钮进行“分支拷贝”
https://gitee.com/WUYUEQbit/

签署贡献者许可协议(CLA)
---------------------------

进入下列项目网址，按照提示进行CLA协议签署
https://gitee.com/organizations/WUYUEQbit/cla/qcos

源码拉取与环境初始化
---------------------------

代码拉取：

.. code-block:: shell

    git clone git@gitee.com:OpenWuYue/qcos.git
    git config --global user.name '名字'
    git config --global user.email 'CLA协议中签署的邮箱'

生成并获取SSH公钥：

.. code-block:: shell

    ssh-keygen -t rsa
    cat ~/.ssh/id_rsa.pub

并在gitee的用户设置->安全设置->SSH公钥，进行公钥的添加:
