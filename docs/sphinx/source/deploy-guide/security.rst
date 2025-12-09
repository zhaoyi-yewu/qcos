安全加固
===========

本章节介绍QCOS的安全加固措施，包括驱动配置文件密码加密和API连接的HTTPS加密配置。

.. contents:: 目录
   :local:
   :depth: 3

自定义驱动配置文件中的账户密码加密
--------------------------------------
驱动配置文件中若需配置远程量子设备API的认证密码，支持明文密码或加密密码两种方式，推荐使用加密密码以提升安全性。

密码加密操作
****************
   进入qcos容器后，使用指定脚本对密码进行加密：

   .. code-block:: shell

      # 进入qcos容器
      docker exec -it qcos bash
      cd bin
      # 执行密码加密脚本（替换my_password为实际密码）
      ./encrypt-password.py -e my_password
      # 脚本输出示例：
      # Original text : my_password
      # Encrypted text: ++gAAAAABo9gU4yf6G9lQQoNpH1LkBSYDsRYs1qNBln_Sf2N5OQP2siY65uaLCoz8-NYFWCfHDj8pCyxHSs4ltSKsdv-yz9muSAQ==

   将加密后的密码填入对应的驱动配置文件中，示例如下：

   .. code-block:: shell

      vim /etc/qcos/conf.d/dummy.toml
      [dummy]
      alias_name = "空载测试设备"
      driver = "DriverDummy"
      password = "++gAAAAABo9gU4yf6G9lQQoNpH1LkBSYDsRYs1qNBln_Sf2N5OQP2siY65uaLCoz8-NYFWCfHDj8pCyxHSs4ltSKsdv-yz9muSAQ=="

密码日志屏蔽规则
*********************
   QCOS会自动屏蔽日志中驱动配置文件的密码字段，只需保证密码字段名包含“password”字符串即可，例如：

   - password
   - user_password
   - my_password
   - my_password_1

   上述字段在日志打印时会被替换为“\*\*\*\*\*\*\*\*”，避免密码泄露。

使用HTTPS加密的API连接
------------------------------
为QCOS API服务配置HTTPS加密连接，需完成证书生成、配置修改、服务重启及客户端适配等步骤。

生成自签名证书（可选）
***************************
   若暂无SSL证书，可使用容器内脚本生成自签名证书，指定IP列表和DNS列表：

   .. code-block:: shell

      # 进入qcos容器
      docker exec -it qcos bash
      cd bin
      # 生成自签名证书（替换IP和DNS为实际值）
      ./make-ssl-cert.py --ip-list 127.0.0.1 --dns-list localhost

   生成的SSL密钥和证书文件默认存放于``/etc/qcos/ssl/``目录下。

修改QCOS配置文件启用SSL
***************************
   编辑QCOS全局配置文件，配置SSL相关参数：

   .. code-block:: shell

      vim /etc/qcos/qcos.toml
      [SSL]
      # 启用API服务器的HTTPS
      USE_SSL = true

      # SSL证书文件路径
      CERT_FILE = "/etc/qcos/ssl/ssl.crt"

      # SSL密钥文件路径
      KEY_FILE = "/etc/qcos/ssl/ssl.key"

      # SSL CA文件路径（可选）
      CA_FILE = "/etc/qcos/ssl/cacert.pem"

重启QCOS服务使配置生效
***************************
   .. code-block:: shell

      docker restart qcos

命令行客户端使用SSL证书
***************************
   命令行工具（qcos-cli）可通过环境变量或命令行参数指定SSL配置：

   .. code-block:: shell

      # 方式1：通过环境变量配置
      export USE_SSL=true
      export SSL_CERTFILE=/etc/qcos/ssl/ssl.crt
      export SSL_KEYFILE=/etc/qcos/ssl/ssl.key
      export SSL_CAFILE=/etc/qcos/ssl/cacert.pem
      qcos-cli version

      # 方式2：通过命令行参数配置
      qcos-cli --use-ssl --ssl-certfile /etc/qcos/ssl/ssl.crt --ssl-keyfile /etc/qcos/ssl/ssl.key --ssl-cafile /etc/qcos/ssl/cacert.pem version
