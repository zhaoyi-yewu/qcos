项目开发规范
===================

本章节介绍了项目开发规范。

.. contents:: 目录
   :local:
   :depth: 3

编码规范
------------------

遵循Python3代码规范，包括: PEP8标准、并可使用ruff检查与修复命令：

- 命名规范（模块名小写 + 下划线 / 类名大驼峰 / 函数名小写 + 下划线 / 常量全大写）：

  - 模块名：driver_utils.py（正确）、DriverUtils.py（错误）
  - 类名：BaseDriver（正确）、base_driver（错误）
  - 函数名：parse_qasm_code()（正确）、ParseQasmCode()（错误）
  - 常量：MAX_RETRY_COUNT = 3（正确）、max_retry_count = 3（错误）
- 注释规范（函数需写Google风格的docstring、复杂逻辑加行注释、驱动类需标注适配设备型号）
- 文件版权声明：使用Mulan PSL v2许可的文件头，可参考同类文件的文件头

接口开发规范
------------------

- 北向API规范：基于JSON-RPC 2.0格式、请求/响应字段要求、错误码定义

驱动开发规范
------------------

- 南向驱动接口规范：新增驱动必须实现的parse()/transpile()/run()等方法，参考drivers/dummy/driver_dummy.py

配置文件规范
------------------

- 设备配置格式要求：设备配置文件需放在conf.d目录下，驱动配置文件必须为toml格式，格式参考dummy.toml
- 【可选】设备配置中涉及到密码加密的，可以使用encrypt-password.py获取加密后的密文，填入配置文件相关密码字段中：

.. code-block:: shell

    # 密码加密命令
    cd bin
    ./encrypt-password.py -e my_password
