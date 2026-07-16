设备分组命令
----------------------

设备分组（Device Group）命令用于创建和管理设备逻辑分组，支持通过命令行创建、查询、更新和删除设备分组。

设备分组创建
***************

创建设备分组的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建设备分组
   usage: qcos-cli create-device-group [-h] [--project-id PROJECT_ID] [--description DESCRIPTION]
                                       [--private] [--device DEVICE [DEVICE ...]]
                                       name

   Create device group for device classification.

   positional arguments:
     name                  Device group name

   options:
     -h, --help            show this help message and exit
     --project-id PROJECT_ID
                           Project ID (UUID, optional)
     --description DESCRIPTION
                           Device group description
     --private             Create as private device group
     --device DEVICE [DEVICE ...]
                           Device names in this group (space-separated)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建设备分组，只包含一个设备
   qcos-cli create-device-group my-group1 --description "simulator" --device dummy

   # 创建设备分组，包含多台设备
   qcos-cli create-device-group my-group2 --description "simulators" --device dummy qutip_sim

设备分组更新
***************

更新设备分组的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新设备分组
   usage: qcos-cli update-device-group [-h] [--name NAME] [--public | --private]
                                      [--project-id PROJECT_ID]
                                      [--description DESCRIPTION | --unset-description]
                                      [--device DEVICE [DEVICE ...] | --unset-device]
                                      group_id

   Update device group by ID or name.

   positional arguments:
     group_id              Device group ID (UUID) or group name

   options:
     -h, --help            show this help message and exit
     --name NAME           Device group name
     --public              Set as public group
     --private             Set as private group
     --project-id PROJECT_ID
                           Project ID (UUID)
     --description DESCRIPTION
                           Device group description
     --unset-description   Unset description field
     --device DEVICE [DEVICE ...]
                           Device names in this group (replaces existing list, space-separated)
     --unset-device        Unset device names list

   对于可空字段，``--{key}`` 用于更新字段值，``--unset-{key}`` 用于清空字段，
   两者互斥不能同时使用。未指定的字段保持原值不变。

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新设备分组（可使用UUID或分组名称）
   qcos-cli update-device-group my-group1 --description "new simulator" --device dummy qutip_sim

   # 清空可空字段
   qcos-cli update-device-group my-group1 --unset-description
   qcos-cli update-device-group my-group1 --unset-device

设备分组详情查询
*****************

查询设备分组详情的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询设备分组详情
   usage: qcos-cli get-device-group [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                                    [--max-width <integer>] [--fit-width] [--print-empty]
                                    group_id

   Get device group by ID or name.

   positional arguments:
     group_id              Device group ID (UUID) or group name

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询设备分组详情（可使用UUID或分组名称）
   qcos-cli get-device-group my-group1

设备分组列表查询
*****************

查询设备分组列表的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询设备分组列表
   usage: qcos-cli list-device-groups [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}]
                                      [--noindent] [--max-width <integer>] [--fit-width] [--print-empty]
                                      [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                      [--group-ids [GROUP_IDS ...]]
                                      [--group-name GROUP_NAME [GROUP_NAME ...]]

   Get device group list.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询设备分组列表
   qcos-cli list-device-groups

   # 按ID列表过滤查询
   qcos-cli list-device-groups --group-ids <group-uuid-1> <group-uuid-2>

   # 按名称过滤查询
   qcos-cli list-device-groups --group-name my-group1

   # 按多个名称过滤查询
   qcos-cli list-device-groups --group-name my-group1 my-group2

设备分组批量删除
****************

批量删除设备分组的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除设备分组（批量）
   usage: qcos-cli delete-device-groups [-h] [-y] group_ids

   Delete device groups by IDs or names (batch).

   positional arguments:
     group_ids             Device group IDs or names to delete. Use comma-separated
                           values for multiple, or 'all' to delete all device groups

   options:
     -h, --help            show this help message and exit
     -y, --yes             Answer yes for all questions

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除单个设备分组（可使用UUID或分组名称）
   qcos-cli delete-device-groups my-group1 -y

   # 批量删除多个设备分组
   qcos-cli delete-device-groups "group1,group2,<uuid3>" -y

   # 删除全部设备分组
   qcos-cli delete-device-groups all -y
