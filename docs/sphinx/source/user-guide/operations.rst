运维指导
===========

本章节介绍QCOS运维相关指导。

.. contents:: 目录
   :local:
   :depth: 3

数据库备份
--------------------------------------

QCOS 使用 PostgreSQL 作为主数据库，定期备份可防止数据丢失。备份通过 ``pg_dump`` 工具导出数据库为 SQL 脚本文件，恢复时可直接执行该脚本重建数据。

**方式一：Docker 环境下备份**

在 Docker 部署环境中，通过 ``docker exec`` 在 PostgreSQL 容器内执行 ``pg_dump``，将数据库导出到宿主机挂载的备份目录：

.. code-block:: shell

   # 在 postgres 容器内执行 pg_dump，导出 qcos 数据库
   docker exec postgres pg_dump \
       --host 127.0.0.1 \
       --username qcos \
       --dbname qcos \
       --file /var/qcos/backup/database/qcos-database.sql

**方式二：使用 export-database.py 脚本备份 (需自行安装匹配PGSQL server的pg_dump命令版本)**

QCOS 提供了 [`bin/export-database.py`](bin/export-database.py:1) 脚本，
支持 sql / csv / json / toml 多种导出格式，
可通过参数指定数据库名称、连接地址、用户名和密码：

.. code-block:: shell

   # 默认导出 qcos 数据库为 sql 文件
   python3 bin/export-database.py

   # 指定数据库、连接地址和输出文件
   python3 bin/export-database.py \
       --db-name qcos \
       --db-url 127.0.0.1:5432 \
       --username qcos \
       --password <password> \
       --output /tmp/qcos-backup.sql

   # 导出为 json 格式
   python3 bin/export-database.py -t json -o /tmp/qcos-backup.json

.. note::

   - 建议通过定时任务（如 crontab）每日自动备份，并保留近 7 天的备份文件。
   - 备份文件应存储在与数据库服务器不同的介质上，避免单点故障导致备份丢失。
   - ``pg_dump`` 方式导出完整数据库（含结构和数据）；
     ``export-database.py`` 的 sql 模式同样使用 ``pg_dump``，
     csv/json/toml 模式则通过 SQLAlchemy 逐表导出数据。
