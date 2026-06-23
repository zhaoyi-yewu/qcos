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
   # PIP_MIRROR地址格式示例: http://mirrors.cmecloud.cn/pypi/simple
   # NPM_MIRROR地址格式示例: http://mirrors.cmecloud.cn/npm/repository/qcos/
   # PYTHON_SRC_MIRROR地址格式示例: https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz
   # PYPY3_BIN_MIRROR地址格式示例: https://downloads.python.org/pypy/pypy3.11-v7.3.20-linux64.tar.bz2
   # 5. DEBUG是内部开发使用的调试开关, 可以配成默认的False
   # 6. LOCAL_CICD是本地CICD的标记开关, 可以配成默认的False
   # 7. REGISTRY为Docker容器私有镜像仓库地址, 如果本机可以访问DockerHub, 则可以留空
